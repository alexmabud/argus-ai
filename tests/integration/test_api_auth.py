"""Testes de integração da API de Autenticação.

Testa endpoints de login, refresh, perfil e upload de foto.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.usuario import Usuario


def _xff_unico() -> dict[str, str]:
    """Gera header X-Forwarded-For com IP unico por chamada.

    Necessario para isolar testes do rate limit acumulado no Redis entre
    execucoes da suite (a chave do limiter usa IP como bucket).
    """
    octeto3 = uuid.uuid4().int % 256
    octeto4 = uuid.uuid4().int % 256
    return {"X-Forwarded-For": f"10.99.{octeto3}.{octeto4}"}


class TestLogin:
    """Testes do endpoint POST /api/v1/auth/login."""

    async def test_login_valido_retorna_tokens(self, client: AsyncClient, usuario: Usuario):
        """Testa login com credenciais válidas retorna tokens.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário com matrícula TEST001.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_senha_errada_retorna_erro(self, client: AsyncClient, usuario: Usuario):
        """Testa login com senha errada retorna 400 ou 401.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "errada"},
        )
        assert response.status_code in (400, 401)

    async def test_login_matricula_inexistente_retorna_erro(self, client: AsyncClient):
        """Testa login com matrícula inexistente retorna erro.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "NAOEXISTE", "senha": "qualquer"},
        )
        assert response.status_code in (400, 401)

    async def test_login_bloqueia_apos_5_falhas(self, client: AsyncClient, usuario: Usuario):
        """Apos 5 senhas erradas, o login com senha CORRETA deve retornar 423.

        Defende contra brute-force; sem lockout, rate limit do XFF e absurdo
        de tentativas em paralelo deixam senha 'admin123' achavel em minutos.

        Usa XFF unico para isolar este teste do rate limit acumulado
        de outros testes na mesma sessao.
        """
        headers = _xff_unico()
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={"matricula": "TEST001", "senha": "errada"},
                headers=headers,
            )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
            headers=headers,
        )
        assert resp.status_code == 423

    async def test_login_sucesso_zera_contador_de_falhas(
        self, client: AsyncClient, db_session: AsyncSession, usuario: Usuario
    ):
        """Login bem-sucedido apos 2 falhas deve zerar tentativas_falhas.

        Garante que o contador nao acumula entre sessoes legitimas:
        usuario que erra a senha 2x e acerta na 3a nao fica perto do bloqueio.
        """
        headers = _xff_unico()
        for _ in range(2):
            await client.post(
                "/api/v1/auth/login",
                json={"matricula": "TEST001", "senha": "errada"},
                headers=headers,
            )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
            headers=headers,
        )
        assert resp.status_code == 200
        await db_session.refresh(usuario)
        assert usuario.tentativas_falhas == 0

    async def test_login_falho_registra_audit(self, client: AsyncClient, db_session: AsyncSession):
        """Falhas de login devem gerar registro de auditoria com acao=LOGIN_FAILED.

        LGPD exige rastreabilidade de tentativas falhas — brute-force nao pode
        passar invisivel. Sem usuario_id (matricula desconhecida ou senha errada
        antes de identificar o user).
        """
        await client.post(
            "/api/v1/auth/login",
            json={"matricula": "naoexiste", "senha": "qualquer"},
        )
        result = await db_session.execute(select(AuditLog).where(AuditLog.acao == "LOGIN_FAILED"))
        registros = result.scalars().all()
        assert len(registros) == 1
        assert registros[0].usuario_id is None


class TestLogout:
    """Testes do endpoint POST /api/v1/auth/logout."""

    async def test_logout_invalida_session_id_server_side(
        self, client: AsyncClient, db_session: AsyncSession, usuario: Usuario
    ):
        """Logout deve zerar session_id no banco — refresh com token antigo falha.

        Antes desta task o logout so limpa o cookie; refresh token continuava
        valido por 30 dias com o mesmo session_id (impossivel revogar).
        """
        headers = _xff_unico()
        login = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
            headers=headers,
        )
        assert login.status_code == 200
        refresh_token = login.json()["refresh_token"]
        access_token = login.json()["access_token"]

        # Logout com Bearer token (autenticado)
        await client.post(
            "/api/v1/auth/logout",
            headers={**headers, "Authorization": f"Bearer {access_token}"},
        )

        # Refresh com token antigo deve falhar (session_id foi limpa)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert resp.status_code in (400, 401)


class TestRefresh:
    """Testes do endpoint POST /api/v1/auth/refresh."""

    async def test_refresh_token_invalido_retorna_erro(self, client: AsyncClient):
        """Testa refresh com token inválido retorna erro.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "token-invalido"},
        )
        assert response.status_code in (400, 401)


class TestMe:
    """Testes do endpoint GET /api/v1/auth/me."""

    async def test_me_autenticado_retorna_usuario(
        self, client: AsyncClient, auth_headers: dict, usuario: Usuario
    ):
        """Testa que /me retorna dados do usuário autenticado.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            usuario: Fixture de usuário.
        """
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["matricula"] == "TEST001"

    async def test_me_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que /me sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestPerfil:
    """Testes do endpoint PUT /api/v1/auth/perfil."""

    async def test_atualizar_perfil_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Testa atualização de perfil retorna 200.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.put(
            "/api/v1/auth/perfil",
            json={"nome": "Agente Atualizado"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Agente Atualizado"

    async def test_atualizar_perfil_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que atualização sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.put(
            "/api/v1/auth/perfil",
            json={"nome": "Hacker"},
        )
        assert response.status_code == 401
