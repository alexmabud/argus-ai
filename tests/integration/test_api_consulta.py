"""Testes de integração da API de Consulta Unificada.

Testa endpoint de busca cross-domain em pessoas, veículos
e abordagens através de um único termo de busca.
"""

from httpx import AsyncClient


class TestConsultaUnificada:
    """Testes do endpoint GET /api/v1/consultas/."""

    async def test_consulta_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Testa que consulta válida retorna 200 com estrutura correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=teste",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "pessoas" in data
        assert "veiculos" in data
        assert "abordagens" in data
        assert "total_resultados" in data

    async def test_consulta_sem_termo_retorna_422(self, client: AsyncClient, auth_headers: dict):
        """Testa que consulta sem termo de busca retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_consulta_sem_auth_retorna_403(self, client: AsyncClient):
        """Testa que consulta sem autenticação retorna 403.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/consultas/?q=teste")
        assert response.status_code == 403

    async def test_consulta_filtro_tipo_pessoa(self, client: AsyncClient, auth_headers: dict):
        """Testa consulta filtrando por tipo 'pessoa'.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=joao&tipo=pessoa",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Quando filtrando por pessoa, veículos e abordagens devem estar vazios
        assert data["veiculos"] == []
        assert data["abordagens"] == []

    async def test_consulta_paginacao(self, client: AsyncClient, auth_headers: dict):
        """Testa que parâmetros de paginação são aceitos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=teste&skip=0&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
