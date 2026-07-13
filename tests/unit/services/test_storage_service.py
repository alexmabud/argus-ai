"""Testes do StorageService — singleton de cliente S3."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import storage_service as ss_module
from app.services.storage_service import storage_key


def test_storage_key_relativo():
    """URL relativa /storage/bucket/key resolve para a chave relativa ao bucket."""
    assert storage_key("/storage/argus-fotos/fotos/uuid.jpg") == "fotos/uuid.jpg"


def test_storage_key_none():
    """URL None não gera chave."""
    assert storage_key(None) is None


def test_storage_key_sem_prefixo_storage():
    """Marcador de valor anonimizado (sem prefixo /storage/) não é uma chave válida."""
    assert storage_key("ANONIMIZADO") is None


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


@pytest.mark.asyncio
async def test_stream_with_meta_retorna_body_e_metadados(monkeypatch):
    """stream_with_meta deve retornar (body, content_type, etag, length).

    O body retornado deve ser o ``StreamingBody`` do S3 (não bytes), para
    permitir streaming via ``iter_chunks`` sem materializar o arquivo
    inteiro em memória.
    """
    fake_body = MagicMock(name="StreamingBody")
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={
            "Body": fake_body,
            "ContentType": "image/jpeg",
            "ETag": '"abc123"',
            "ContentLength": 4096,
        }
    )

    async def fake_aenter(self):
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
        body, content_type, etag, length = await service.stream_with_meta("k")
    finally:
        await service.shutdown()

    assert body is fake_body
    assert content_type == "image/jpeg"
    assert etag == '"abc123"'
    assert length == 4096
    # Não pode ter chamado .read() — streaming, não buffer
    fake_body.read.assert_not_called() if hasattr(fake_body.read, "assert_not_called") else None


@pytest.mark.asyncio
async def test_stream_with_meta_repassa_if_none_match(monkeypatch):
    """Quando if_none_match é informado, deve ir como IfNoneMatch ao get_object."""
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={
            "Body": MagicMock(),
            "ContentType": "image/png",
            "ETag": '"xyz"',
            "ContentLength": 10,
        }
    )

    async def fake_aenter(self):
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
        await service.stream_with_meta("k", if_none_match='"xyz"')
    finally:
        await service.shutdown()

    kwargs = fake_client.get_object.call_args.kwargs
    assert kwargs.get("IfNoneMatch") == '"xyz"'
    assert kwargs.get("Key") == "k"


@pytest.mark.asyncio
async def test_stream_with_meta_omite_if_none_match_quando_none(monkeypatch):
    """Sem if_none_match, o get_object não deve receber IfNoneMatch."""
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={
            "Body": MagicMock(),
            "ContentType": "image/png",
            "ETag": '"xyz"',
            "ContentLength": 10,
        }
    )

    async def fake_aenter(self):
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
        await service.stream_with_meta("k")
    finally:
        await service.shutdown()

    kwargs = fake_client.get_object.call_args.kwargs
    assert "IfNoneMatch" not in kwargs


@pytest.mark.asyncio
async def test_stream_with_meta_fallback_content_type(monkeypatch):
    """Quando S3 não devolve ContentType, usa application/octet-stream."""
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={"Body": MagicMock()}  # sem ContentType/ETag/Length
    )

    async def fake_aenter(self):
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
        _, content_type, etag, length = await service.stream_with_meta("k")
    finally:
        await service.shutdown()

    assert content_type == "application/octet-stream"
    assert etag is None
    assert length is None
