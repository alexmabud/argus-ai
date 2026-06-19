"""Testes do WatermarkService (cache MinIO + fail-closed escopado)."""

import io
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError
from PIL import Image

from app.services.watermark_service import WatermarkService


def _img(size: tuple[int, int] = (800, 600)) -> bytes:
    """Gera bytes de imagem JPEG sólida para os testes.

    Args:
        size: Dimensões (largura, altura).

    Returns:
        Bytes JPEG da imagem gerada.
    """
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def _nosuchkey() -> ClientError:
    """Gera ClientError de NoSuchKey do S3.

    Returns:
        ClientError simulando chave inexistente no S3.
    """
    return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


@pytest.fixture
def fake_storage(monkeypatch):
    """Substitui StorageService.get() por um mock com download/upload async.

    Args:
        monkeypatch: Fixture pytest para patch temporário.

    Returns:
        AsyncMock representando a instância do StorageService.
    """
    from app.services import watermark_service as mod

    storage = AsyncMock()
    monkeypatch.setattr(mod.StorageService, "get", classmethod(lambda cls: storage))
    return storage


async def test_cache_hit_nao_rebaixa_original(fake_storage):
    """Hit no cache devolve a variante sem baixar o original."""
    marcada = _img()
    fake_storage.download_with_meta = AsyncMock(return_value=(marcada, "image/jpeg"))
    svc = WatermarkService()
    res = await svc.get_or_create("fotos/uuid_x.jpg", "GM-1", "image/jpeg")
    assert res.is_image is True
    assert res.body == marcada
    fake_storage.download_with_meta.assert_awaited_once()  # só o cache, não o original


async def test_cache_miss_gera_marca_e_faz_upload(fake_storage):
    """Miss baixa o original, marca, faz upload da variante e devolve marcada."""
    original = _img()
    # 1ª chamada (cache) -> NoSuchKey ; 2ª (original) -> bytes originais
    fake_storage.download_with_meta = AsyncMock(
        side_effect=[_nosuchkey(), (original, "image/jpeg")]
    )
    fake_storage.upload = AsyncMock()
    svc = WatermarkService()
    res = await svc.get_or_create("fotos/uuid_x.jpg", "GM-1", "image/jpeg")
    assert res.is_image is True
    assert res.body != original
    fake_storage.upload.assert_awaited_once()


async def test_octet_stream_que_e_imagem_e_marcado(fake_storage):
    """Content-type ambíguo (octet-stream) que é imagem ainda é marcado (sniff)."""
    original = _img()
    fake_storage.download_with_meta = AsyncMock(
        side_effect=[_nosuchkey(), (original, "application/octet-stream")]
    )
    fake_storage.upload = AsyncMock()
    svc = WatermarkService()
    res = await svc.get_or_create("fotos/uuid_x.bin", "GM-1", "application/octet-stream")
    assert res.is_image is True
    assert res.body != original


async def test_nao_imagem_faz_passthrough(fake_storage):
    """Conteúdo que não é imagem (PDF disfarçado) passa sem marca."""
    pdf = b"%PDF-1.7 fake"
    fake_storage.download_with_meta = AsyncMock(
        side_effect=[_nosuchkey(), (pdf, "application/octet-stream")]
    )
    fake_storage.upload = AsyncMock()
    svc = WatermarkService()
    res = await svc.get_or_create("fotos/uuid_x.bin", "GM-1", "application/octet-stream")
    assert res.is_image is False
    assert res.body == pdf
    fake_storage.upload.assert_not_awaited()


async def test_render_falha_em_imagem_propaga_failclosed(fake_storage, monkeypatch):
    """Imagem confirmada cujo render falha propaga exceção (proxy -> 500)."""
    original = _img()
    fake_storage.download_with_meta = AsyncMock(
        side_effect=[_nosuchkey(), (original, "image/jpeg")]
    )
    from app.services import watermark_service as mod

    def boom(*a, **k):
        """Stub que simula falha no render da marca."""
        raise RuntimeError("render quebrou")

    monkeypatch.setattr(mod, "burn_watermark", boom)
    svc = WatermarkService()
    with pytest.raises(RuntimeError):
        await svc.get_or_create("fotos/uuid_x.jpg", "GM-1", "image/jpeg")
