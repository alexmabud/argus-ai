"""Testes de integração da API de Analytics.

Testa endpoints de métricas operacionais: resumo, mapa de calor,
horários de pico, pessoas recorrentes e qualidade RAG.
"""

from httpx import AsyncClient


class TestResumo:
    """Testes do endpoint GET /api/v1/analytics/resumo."""

    async def test_resumo_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar resumo operacional com status 200.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/resumo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_abordagens" in data
        assert "total_pessoas_distintas" in data
        assert "media_abordagens_dia" in data

    async def test_resumo_com_dias_customizado(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar parâmetro dias.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/resumo?dias=7",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["periodo_dias"] == 7

    async def test_resumo_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/analytics/resumo")
        assert response.status_code == 403


class TestMapaCalor:
    """Testes do endpoint GET /api/v1/analytics/mapa-calor."""

    async def test_mapa_calor_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pontos (pode ser vazia).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/mapa-calor",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestHorariosPico:
    """Testes do endpoint GET /api/v1/analytics/horarios-pico."""

    async def test_horarios_pico_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de horários com total.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/horarios-pico",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPessoasRecorrentes:
    """Testes do endpoint GET /api/v1/analytics/pessoas-recorrentes."""

    async def test_pessoas_recorrentes_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pessoas (pode ser vazia).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/pessoas-recorrentes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestRAGQualidade:
    """Testes do endpoint GET /api/v1/analytics/rag-qualidade."""

    async def test_rag_qualidade_retorna_metricas(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar métricas RAG com totais.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/rag-qualidade",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_ocorrencias" in data
        assert "ocorrencias_indexadas" in data
