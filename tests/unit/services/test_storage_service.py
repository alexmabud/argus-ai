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


@pytest.mark.asyncio
async def test_get_retorna_mesma_instancia():
    """StorageService.get() retorna a mesma instância em chamadas repetidas."""
    ss_module.StorageService._instance = None
    try:
        a = ss_module.StorageService.get()
        b = ss_module.StorageService.get()
        assert a is b
    finally:
        ss_module.StorageService._instance = None


@pytest.mark.asyncio
async def test_startup_idempotente(monkeypatch):
    """Chamar startup() múltiplas vezes não recria o cliente."""
    fake_client = MagicMock()
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
    await service.startup()
    await service.startup()
    try:
        assert create_calls["n"] == 1
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_ensure_client_levanta_se_nao_startup_ado():
    """Operações antes de startup() devem levantar RuntimeError claro."""
    service = ss_module.StorageService()
    with pytest.raises(RuntimeError, match="startup"):
        await service.upload(b"x", "k")
