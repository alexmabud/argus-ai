"""Testes do StorageService — singleton de cliente S3."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import storage_service as ss_module


@pytest.mark.asyncio
async def test_storage_service_reutiliza_cliente_entre_chamadas(monkeypatch):
    """O cliente S3 deve ser criado uma única vez e reusado."""
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={
            "Body": AsyncMock(read=AsyncMock(return_value=b"x")),
            "ContentType": "image/jpeg",
        }
    )
    create_calls = {"n": 0}

    async def fake_aenter(self):
        create_calls["n"] += 1
        return fake_client

    async def fake_aexit(self, *a):
        return None

    monkeypatch.setattr(
        ss_module.aioboto3.Session,
        "client",
        lambda self, *a, **kw: type(
            "CM", (), {"__aenter__": fake_aenter, "__aexit__": fake_aexit}
        )(),
    )

    service = ss_module.StorageService()
    await service.startup()
    try:
        await service.download_with_meta("k1")
        await service.download_with_meta("k2")
        await service.download_with_meta("k3")
    finally:
        await service.shutdown()

    assert create_calls["n"] == 1, "cliente S3 deveria ser criado 1× e reusado"
