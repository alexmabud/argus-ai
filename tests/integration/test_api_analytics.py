"""Testes de integração da API de Analytics.

Testa endpoints de métricas operacionais: resumo, mapa de calor,
horários de pico e pessoas recorrentes.
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


class TestResumoHoje:
    """Testes do endpoint GET /api/v1/analytics/resumo-hoje."""

    async def test_resumo_hoje_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-hoje", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data

    async def test_resumo_hoje_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/analytics/resumo-hoje")
        assert response.status_code == 403


class TestResumoMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-mes."""

    async def test_resumo_mes_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-mes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestResumoTotalEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-total."""

    async def test_resumo_total_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar totais históricos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-total", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestPorDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-dia."""

    async def test_por_dia_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-dia", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_por_dia_aceita_parametro_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar parâmetro dias.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-dia?dias=7", headers=auth_headers)
        assert response.status_code == 200


class TestPorMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-mes."""

    async def test_por_mes_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-mes", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDiasComAbordagemEndpoint:
    """Testes do endpoint GET /api/v1/analytics/dias-com-abordagem."""

    async def test_retorna_lista_de_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de dias com abordagem no mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=2026-03",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_mes_invalido_retorna_422(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 422 para formato de mês inválido.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=invalido",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestPessoasDoDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/pessoas-do-dia."""

    async def test_retorna_lista_de_pessoas(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pessoas abordadas no dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/pessoas-do-dia?data=2026-03-14",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
