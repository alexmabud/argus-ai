"""Testes de integração dos endpoints de health check.

/health é raso por design (probe externo de produção, nunca deve falhar
por instabilidade transitória de dependência). /health/ready testa DB e
Redis de verdade — usado pelo HEALTHCHECK do container de desenvolvimento
(achado #29/2026-07-13).
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_retorna_200_sempre(client: AsyncClient):
    """/health responde 200 com payload simples, sem tocar DB/Redis."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "Argus AI"}


@pytest.mark.asyncio
async def test_health_ready_ok_quando_db_e_redis_disponiveis(client: AsyncClient):
    """/health/ready responde 200 quando DB e Redis reais estão acessíveis."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": True, "redis": True}


@pytest.mark.asyncio
async def test_health_ready_503_quando_redis_indisponivel(client: AsyncClient):
    """/health/ready responde 503 e reporta checks.redis=False se Redis falhar.

    Achado #29/2026-07-13: antes, o HEALTHCHECK do container dev só batia em
    /health (sempre 200) — um Redis fora do ar não derrubava o container.
    """
    with patch("app.api.health.aioredis.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=ConnectionError("redis indisponível"))
        mock_client.aclose = AsyncMock()
        mock_from_url.return_value = mock_client

        resp = await client.get("/health/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] is False
    assert body["checks"]["database"] is True
