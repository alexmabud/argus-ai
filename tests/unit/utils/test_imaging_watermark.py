"""Testes da função de marca d'água queimada (camada 2 do watermark rastreável)."""

import io

import pytest
from PIL import Image, UnidentifiedImageError

from app.utils.imaging import burn_watermark


def _imagem_fake(fmt: str = "JPEG", size: tuple[int, int] = (800, 600)) -> bytes:
    """Gera bytes de uma imagem sólida para os testes.

    Args:
        fmt: Formato de saída (JPEG, PNG, WEBP).
        size: Dimensões (largura, altura).

    Returns:
        Bytes da imagem no formato pedido.
    """
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 120, 120)).save(buf, format=fmt)
    return buf.getvalue()


def test_burn_watermark_preserva_dimensoes_e_abre_limpo():
    """A imagem marcada mantém as dimensões e continua sendo imagem válida."""
    original = _imagem_fake(size=(800, 600))
    marcada = burn_watermark(original, "GM-12345")
    img = Image.open(io.BytesIO(marcada))
    assert img.size == (800, 600)


def test_burn_watermark_altera_pixels():
    """A marca efetivamente altera os bytes (não devolve o original)."""
    original = _imagem_fake()
    assert burn_watermark(original, "GM-12345") != original


def test_burn_watermark_deterministico():
    """Mesmo (bytes, matrícula) gera a mesma saída (necessário para cache)."""
    original = _imagem_fake()
    assert burn_watermark(original, "GM-12345") == burn_watermark(original, "GM-12345")


def test_burn_watermark_difere_por_matricula():
    """Matrículas diferentes geram saídas diferentes."""
    original = _imagem_fake()
    assert burn_watermark(original, "GM-11111") != burn_watermark(original, "GM-22222")


def test_burn_watermark_funciona_em_thumbnail_pequeno():
    """Marca tudo: thumbnails pequenos também recebem a marca sem quebrar."""
    original = _imagem_fake(size=(150, 150))
    marcada = burn_watermark(original, "GM-12345")
    assert Image.open(io.BytesIO(marcada)).size == (150, 150)


def test_burn_watermark_nao_imagem_levanta_unidentified():
    """Bytes que não são imagem propagam UnidentifiedImageError (sniff)."""
    with pytest.raises(UnidentifiedImageError):
        burn_watermark(b"%PDF-1.7 not an image", "GM-12345")


def test_burn_watermark_marca_heic_de_iphone():
    """Foto HEIC (iPhone) é marcada e re-codificada em JPEG.

    Regressão: o decoder HEIF precisa estar registrado no próprio imaging.py
    (a marca roda no proxy /storage, fora do fluxo de upload). Sem isso, fotos
    de iPhone armazenadas como HEIC eram servidas sem marca d'água.
    """
    pytest.importorskip("pillow_heif")
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (70, 90, 110)).save(buf, format="HEIF")
    heic_bytes = buf.getvalue()

    marcada = burn_watermark(heic_bytes, "GM-12345")
    assert marcada != heic_bytes
    img = Image.open(io.BytesIO(marcada))
    assert img.format == "JPEG"  # servido como image/jpeg
    assert img.size == (400, 300)
