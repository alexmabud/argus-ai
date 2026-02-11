"""Testes da API de autenticação (register, login, refresh, me).

Testa os endpoints de autenticação incluindo validação de credenciais,
geração de tokens, refresh de sessões e obtenção de dados do usuário atual.
"""

from httpx import AsyncClient

from app.core.security import criar_access_token, criar_refresh_token


class TestRegister:
    """Testes do endpoint de registro de usuário."""

    async def test_register_success(self, client: AsyncClient, guarnicao):
        """Testa registro bem-sucedido de novo usuário.

        Verifica se o endpoint retorna status 201 e os dados do usuário
        criado, garantindo que senhas nunca são retornadas na resposta.

        Args:
            client: Cliente HTTP assincrónico para testes.
            guarnicao: Fixture de guarnição para associar ao novo usuário.
        """
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "nome": "Novo Agente",
                "matricula": "NEW001",
                "senha": "senha123",
                "guarnicao_id": guarnicao.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["matricula"] == "NEW001"
        assert data["nome"] == "Novo Agente"
        assert "senha" not in data
        assert "senha_hash" not in data

    async def test_register_duplicate_matricula(self, client: AsyncClient, usuario):
        """Testa rejeição de registro com matrícula duplicada.

        Verifica se o endpoint retorna status 409 (Conflict) ao tentar
        registrar um usuário com matrícula já existente.

        Args:
            client: Cliente HTTP assincrónico para testes.
            usuario: Fixture de usuário existente com matrícula TEST001.
        """
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "nome": "Outro Agente",
                "matricula": usuario.matricula,
                "senha": "senha123",
                "guarnicao_id": usuario.guarnicao_id,
            },
        )
        assert response.status_code == 409


class TestLogin:
    """Testes do endpoint de login de usuário."""

    async def test_login_success(self, client: AsyncClient, usuario):
        """Testa login bem-sucedido com credenciais válidas.

        Verifica se o endpoint retorna status 200 e tokens válidos
        (access_token e refresh_token) com tipo bearer.

        Args:
            client: Cliente HTTP assincrónico para testes.
            usuario: Fixture de usuário com credenciais TEST001/senha123.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "matricula": usuario.matricula,
                "senha": "senha123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, usuario):
        """Testa rejeição de login com senha incorreta.

        Verifica se o endpoint retorna status 401 (Unauthorized) ao
        tentar login com senha inválida.

        Args:
            client: Cliente HTTP assincrónico para testes.
            usuario: Fixture de usuário para validar com senha errada.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "matricula": usuario.matricula,
                "senha": "senhaerrada",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Testa rejeição de login com usuário inexistente.

        Verifica se o endpoint retorna status 401 (Unauthorized) ao
        tentar login com matrícula que não existe no banco.

        Args:
            client: Cliente HTTP assincrónico para testes.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "matricula": "NAOEXISTE",
                "senha": "senha123",
            },
        )
        assert response.status_code == 401


class TestRefresh:
    """Testes do endpoint de refresh de token."""

    async def test_refresh_success(self, client: AsyncClient, usuario):
        """Testa renovação bem-sucedida de access_token com refresh_token.

        Verifica se o endpoint retorna status 200 e novos tokens válidos
        quando um refresh_token válido é fornecido.

        Args:
            client: Cliente HTTP assincrónico para testes.
            usuario: Fixture de usuário para gerar token de refresh.
        """
        refresh = criar_refresh_token(
            {
                "sub": str(usuario.id),
                "guarnicao_id": usuario.guarnicao_id,
            }
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_access_token_fails(self, client: AsyncClient, usuario):
        """Testa rejeição ao usar access_token no lugar de refresh_token.

        Verifica se o endpoint retorna status 401 ao receber um access_token
        em vez de um refresh_token válido, garantindo separação de tipos.

        Args:
            client: Cliente HTTP assincrónico para testes.
            usuario: Fixture de usuário para gerar token de acesso.
        """
        access = criar_access_token(
            {
                "sub": str(usuario.id),
                "guarnicao_id": usuario.guarnicao_id,
            }
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access},
        )
        assert response.status_code == 401


class TestMe:
    """Testes do endpoint que retorna dados do usuário autenticado."""

    async def test_me_authenticated(self, client: AsyncClient, auth_headers):
        """Testa obtenção bem-sucedida de dados do usuário autenticado.

        Verifica se o endpoint retorna status 200 e os dados corretos do
        usuário quando um header Authorization válido é fornecido.

        Args:
            client: Cliente HTTP assincrónico para testes.
            auth_headers: Fixture com header Authorization contendo Bearer token.
        """
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "matricula" in data
        assert "nome" in data

    async def test_me_unauthenticated(self, client: AsyncClient):
        """Testa rejeição de acesso sem autenticação.

        Verifica se o endpoint retorna status 403 (Forbidden) quando
        nenhum header Authorization é fornecido.

        Args:
            client: Cliente HTTP assincrónico para testes.
        """
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403
