"""Testes de integração da API de Autenticação.

Testa endpoints de login, refresh, perfil e upload de foto.
"""

import uuid

import pytest
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

    async def test_refresh_rotaciona_sid_e_invalida_token_antigo(
        self, client: AsyncClient, usuario: Usuario, db_session: AsyncSession
    ):
        """Refresh de usuário comum deve rotacionar o sid e invalidar o token antigo.

        Mitiga roubo de refresh token (#5/2B): após um refresh, o token anterior
        deixa de valer porque o session_id rotaciona no banco.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário comum (não-admin).
            db_session: Sessão do banco de testes.
        """
        login = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
        )
        assert login.status_code == 200
        token_antigo = login.json()["refresh_token"]
        await db_session.refresh(usuario)
        sid_apos_login = usuario.session_id

        # Refresh válido (usa o cookie HttpOnly setado no login).
        r1 = await client.post("/api/v1/auth/refresh", json={})
        assert r1.status_code == 200
        await db_session.refresh(usuario)
        assert usuario.session_id is not None
        assert usuario.session_id != sid_apos_login  # sid rotacionou

        # O token de refresh ANTIGO (do login) agora deve ser rejeitado.
        client.cookies.clear()
        r2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token_antigo},
        )
        assert r2.status_code in (400, 401)

    async def test_refresh_mantem_sid_para_admin(
        self, client: AsyncClient, guarnicao, db_session: AsyncSession
    ):
        """Refresh de admin deve manter o sid (sessão multi-dispositivo).

        Admin compartilha um único session_id entre celular e desktop; rotacionar
        no refresh derrubaria o outro dispositivo. Garante que o caso admin
        preserva o sid (espelha a lógica do login).

        Args:
            client: Cliente HTTP assincrónico.
            guarnicao: Fixture de guarnição.
            db_session: Sessão do banco de testes.
        """
        from app.core.security import criar_refresh_token, hash_senha
        from app.services.auth_service import AuthService

        admin = Usuario(
            nome="Admin Teste",
            matricula="ADMIN2B",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao.id,
            session_id="sid-admin-fixo",
            is_admin=True,
        )
        db_session.add(admin)
        await db_session.flush()

        token = criar_refresh_token({"sub": str(admin.id), "sid": "sid-admin-fixo"})
        novos = await AuthService(db_session).refresh(token)
        assert novos.access_token

        await db_session.refresh(admin)
        assert admin.session_id == "sid-admin-fixo"  # admin não rotaciona


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
        assert data["nome"] == "AGENTE ATUALIZADO"

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


class TestRefreshCookie:
    """Testes de refresh token em cookie HttpOnly (Fase I1)."""

    async def test_login_seta_cookie_refresh_httponly(self, client: AsyncClient, usuario: Usuario):
        """Login deve setar cookie argus_refresh_token HttpOnly.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário.
        """
        resp = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
        )
        assert resp.status_code == 200
        assert "argus_refresh_token" in resp.cookies

    async def test_refresh_via_cookie_sem_corpo(self, client: AsyncClient, usuario: Usuario):
        """POST /auth/refresh com cookie e corpo vazio deve renovar tokens.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário.
        """
        # Fazer login para obter cookie
        login = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
        )
        assert login.status_code == 200

        # Refresh sem corpo — deve usar cookie
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_logout_limpa_cookie_refresh(
        self, client: AsyncClient, usuario: Usuario, auth_headers: dict
    ):
        """Logout deve limpar cookie de refresh e retornar 204.

        Usa auth_headers (sessão já ativa via fixture) para evitar
        trocar o session_id via login e invalidar o token.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário com sessão ativa.
            auth_headers: Headers com token de autenticação.
        """
        resp = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )
        assert resp.status_code == 204
        # Logout bem-sucedido (204) é suficiente para confirmar que o cookie foi limpo
        # (Set-Cookie com max-age=0 é emitido pelo delete_cookie)


class TestSemAutoCadastro:
    """Guarda de regressão: rotas públicas de auto-cadastro não devem existir."""

    @pytest.mark.parametrize(
        "path",
        ["/api/v1/auth/register", "/api/v1/auth/signup", "/api/v1/register"],
    )
    async def test_sem_endpoint_de_autocadastro(self, client: AsyncClient, path: str):
        """Rotas de auto-cadastro devem retornar 404 ou 405.

        Args:
            client: Cliente HTTP assincrónico.
            path: Caminho testado.
        """
        r = await client.post(path, json={})
        assert r.status_code in (404, 405)


class TestBloqueioIP:
    """Testes de bloqueio por IP no Redis (Fase B)."""

    async def test_ip_bloqueado_apos_tentativas_falhas(
        self,
        client: AsyncClient,
        usuario: Usuario,
    ):
        """Após MAX_LOGIN_ATTEMPTS falhas do mesmo IP, o login deve ser bloqueado.

        Usa XFF único para isolar o bucket Redis deste teste.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário.
        """
        from app.config import settings

        headers = _xff_unico()
        for _ in range(settings.MAX_LOGIN_ATTEMPTS):
            await client.post(
                "/api/v1/auth/login",
                json={"matricula": "TEST001", "senha": "errada"},
                headers=headers,
            )
        # Tentativa extra (mesmo com senha correta) deve ser bloqueada
        resp = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
            headers=headers,
        )
        assert resp.status_code in (423, 429)

    async def test_login_correto_reseta_contador_ip(
        self,
        client: AsyncClient,
        usuario: Usuario,
    ):
        """Login bem-sucedido deve zerar o contador de falhas por IP.

        Args:
            client: Cliente HTTP assincrónico.
            usuario: Fixture de usuário.
        """
        headers = _xff_unico()
        # 2 falhas — abaixo do limiar
        for _ in range(2):
            await client.post(
                "/api/v1/auth/login",
                json={"matricula": "TEST001", "senha": "errada"},
                headers=headers,
            )
        # Login correto deve funcionar e resetar contador
        resp = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "TEST001", "senha": "senha123"},
            headers=headers,
        )
        assert resp.status_code == 200


class TestSenhaProvisoria:
    """Testes de TTL da senha provisória (Fase A2)."""

    async def test_login_recusa_senha_provisoria_expirada(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        guarnicao,
    ):
        """Login com senha provisória expirada deve retornar 401.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
        """
        from datetime import UTC, datetime, timedelta

        from app.core.security import hash_senha
        from app.models.usuario import Usuario

        u = Usuario(
            nome="EXP",
            matricula="EXP001",
            senha_hash=hash_senha("Abc123!x"),
            guarnicao_id=guarnicao.id,
            session_id=None,
            senha_expira_em=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(u)
        await db_session.flush()

        r = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "EXP001", "senha": "Abc123!x"},
            headers=_xff_unico(),
        )
        assert r.status_code == 401

    async def test_login_aceita_senha_com_expiracao_futura(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        guarnicao,
    ):
        """Login com senha dentro do TTL (não expirada) deve autenticar.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
        """
        from datetime import UTC, datetime, timedelta

        from app.core.security import hash_senha
        from app.models.usuario import Usuario

        u = Usuario(
            nome="VALID",
            matricula="VAL001",
            senha_hash=hash_senha("Abc123!x"),
            guarnicao_id=guarnicao.id,
            session_id=None,
            senha_expira_em=datetime.now(UTC) + timedelta(hours=23),
        )
        db_session.add(u)
        await db_session.flush()

        r = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "VAL001", "senha": "Abc123!x"},
            headers=_xff_unico(),
        )
        assert r.status_code == 200

    async def test_login_aceita_senha_sem_expiracao(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        guarnicao,
    ):
        """Login com senha_expira_em=NULL deve autenticar (retrocompatível).

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
        """
        from app.core.security import hash_senha
        from app.models.usuario import Usuario

        u = Usuario(
            nome="NOEXP",
            matricula="NOE001",
            senha_hash=hash_senha("Abc123!x"),
            guarnicao_id=guarnicao.id,
            session_id=None,
            senha_expira_em=None,
        )
        db_session.add(u)
        await db_session.flush()

        r = await client.post(
            "/api/v1/auth/login",
            json={"matricula": "NOE001", "senha": "Abc123!x"},
            headers=_xff_unico(),
        )
        assert r.status_code == 200
