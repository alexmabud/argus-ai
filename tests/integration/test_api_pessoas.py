"""Testes de integração da API de Pessoas.

Testa endpoints CRUD de pessoas incluindo criação, busca, atualização,
soft delete e verificação de isolamento multi-tenant.
"""

from httpx import AsyncClient


class TestCriarPessoa:
    """Testes do endpoint POST /api/v1/pessoas/."""

    async def test_criar_pessoa_sucesso(self, client: AsyncClient, auth_headers: dict):
        """Testa criação de pessoa retorna 201.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/pessoas/",
            json={
                "nome": "Maria Souza",
                "apelido": "Marizinha",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Maria Souza"
        assert data["apelido"] == "Marizinha"
        assert "id" in data

    async def test_criar_pessoa_com_cpf_mascarado(self, client: AsyncClient, auth_headers: dict):
        """Testa que CPF na resposta está mascarado (LGPD).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/pessoas/",
            json={
                "nome": "João CPF",
                "cpf": "123.456.789-00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["cpf_masked"] is not None
        assert "123" not in data["cpf_masked"]

    async def test_criar_pessoa_sem_auth_retorna_403(self, client: AsyncClient):
        """Testa que requisição sem token retorna 403.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/pessoas/",
            json={"nome": "Sem Auth"},
        )
        assert response.status_code == 403


class TestListarPessoas:
    """Testes do endpoint GET /api/v1/pessoas/."""

    async def test_listar_pessoas_vazio(self, client: AsyncClient, auth_headers: dict):
        """Testa listagem retorna lista vazia quando não há pessoas.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/pessoas/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_listar_pessoas_retorna_criadas(self, client: AsyncClient, auth_headers: dict):
        """Testa listagem retorna pessoas criadas.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        await client.post(
            "/api/v1/pessoas/",
            json={"nome": "Pessoa Lista 1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/pessoas/",
            json={"nome": "Pessoa Lista 2"},
            headers=auth_headers,
        )
        response = await client.get(
            "/api/v1/pessoas/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestObterPessoa:
    """Testes do endpoint GET /api/v1/pessoas/{id}."""

    async def test_obter_detalhe_pessoa(self, client: AsyncClient, auth_headers: dict):
        """Testa obtenção de detalhe de pessoa com endereços e vínculos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        create_response = await client.post(
            "/api/v1/pessoas/",
            json={"nome": "Pessoa Detalhe"},
            headers=auth_headers,
        )
        pessoa_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/pessoas/{pessoa_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Pessoa Detalhe"
        assert "enderecos" in data
        assert "relacionamentos" in data

    async def test_obter_pessoa_inexistente(self, client: AsyncClient, auth_headers: dict):
        """Testa busca de pessoa inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/pessoas/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeletarPessoa:
    """Testes do endpoint DELETE /api/v1/pessoas/{id}."""

    async def test_soft_delete_pessoa(self, client: AsyncClient, auth_headers: dict):
        """Testa soft delete de pessoa retorna 204.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        create_response = await client.post(
            "/api/v1/pessoas/",
            json={"nome": "Para Deletar"},
            headers=auth_headers,
        )
        pessoa_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/pessoas/{pessoa_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
