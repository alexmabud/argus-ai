"""Testes de integração da API de Autenticação.

Testa endpoints de login, refresh, perfil e upload de foto.
"""

from httpx import AsyncClient

from app.models.usuario import Usuario


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
