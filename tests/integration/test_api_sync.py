"""Testes de integração da API de Sincronização.

Testa endpoint POST /sync/batch com itens válidos,
inválidos e deduplicação por client_id.
"""

from httpx import AsyncClient


class TestSyncBatch:
    """Testes do endpoint POST /api/v1/sync/batch."""

    async def test_sync_batch_tipo_invalido(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar erro para tipo desconhecido.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={
                "items": [
                    {
                        "client_id": "test-uuid-1",
                        "tipo": "tipo_invalido",
                        "dados": {"foo": "bar"},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "error"
        assert data["results"][0]["client_id"] == "test-uuid-1"

    async def test_sync_batch_vazio(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar batch vazio sem erro.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={"items": []},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["results"] == []

    async def test_sync_batch_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={"items": []},
        )
        assert response.status_code == 403
