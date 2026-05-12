"""Testes do gerador de thumbnails."""

import io

from PIL import Image

from app.utils.imaging import gerar_thumbnail


def _imagem_dummy(width: int, height: int, fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95)
    return buf.getvalue()


def test_thumbnail_300px_largura():
    """Thumb deve ter no máximo 300px de largura."""
    src = _imagem_dummy(2400, 1600)
    thumb_bytes = gerar_thumbnail(src, max_width=300, quality=75)
    img = Image.open(io.BytesIO(thumb_bytes))
    assert img.width == 300
    assert img.height == 200  # mantém proporção 3:2


def test_thumbnail_nao_upscale_imagem_pequena():
    """Imagem menor que max_width deve permanecer com tamanho original."""
    src = _imagem_dummy(150, 100)
    thumb_bytes = gerar_thumbnail(src, max_width=300, quality=75)
    img = Image.open(io.BytesIO(thumb_bytes))
    assert img.width == 150
    assert img.height == 100


def test_thumbnail_sempre_jpeg():
    """Output sempre é JPEG independente do formato de entrada."""
    src_png = _imagem_dummy(800, 800, fmt="PNG")
    thumb_bytes = gerar_thumbnail(src_png)
    img = Image.open(io.BytesIO(thumb_bytes))
    assert img.format == "JPEG"


def test_thumbnail_compactacao_efetiva():
    """Thumb 300px JPEG q75 deve ser bem menor que a original."""
    src = _imagem_dummy(2400, 1600)
    thumb_bytes = gerar_thumbnail(src)
    assert len(thumb_bytes) < len(src) * 0.1  # < 10% do tamanho
