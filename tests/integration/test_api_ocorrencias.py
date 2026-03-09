"""Testes de integração da API de Ocorrências.

Testa endpoints de busca de ocorrências por nome, número RAP e data.
"""

from httpx import AsyncClient

from app.models.ocorrencia import Ocorrencia


class TestBuscarOcorrencias:
    """Testes do endpoint GET /api/v1/ocorrencias/buscar."""

    async def test_busca_por_nome_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome encontra ocorrência com esse nome no texto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com texto contendo "Carlos Eduardo".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Carlos Eduardo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_rap_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por número RAP parcial retorna a ocorrência correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com número "RAP 2026/000001".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?rap=2026/000001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_data_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por data de criação retorna ocorrência correta.

        Usa data UTC para coincidir com o timestamp armazenado pelo banco,
        que opera em UTC independente do fuso local do cliente.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência criada hoje.
        """
        from datetime import UTC, datetime

        hoje_utc = datetime.now(UTC).date().isoformat()
        response = await client.get(
            f"/api/v1/ocorrencias/buscar?data={hoje_utc}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_busca_sem_filtros_retorna_lista_vazia(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que busca sem filtros retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_nome_inexistente_retorna_vazio(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome que não existe retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência (garante dado no banco).
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=NomeQueNaoExiste",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que busca sem autenticação retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/ocorrencias/buscar?nome=Carlos")
        assert response.status_code == 401
