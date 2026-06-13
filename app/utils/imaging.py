"""Utilitários de processamento de imagem (geração de thumbnails).

Usado por FotoService para gerar versão reduzida (~25KB) de fotos
de pessoas e abordagens, servida em listagens. Reduz drasticamente
tráfego do proxy /storage quando há muitas fotos por tela.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps


def gerar_thumbnail(
    image_bytes: bytes,
    max_width: int = 300,
    quality: int = 75,
) -> bytes:
    """Gera thumbnail JPEG reduzido respeitando proporção original.

    Aplica também ``ImageOps.exif_transpose`` para corrigir orientação
    de fotos de celular (EXIF rotation).

    Args:
        image_bytes: Bytes da imagem original (JPEG, PNG, WEBP).
        max_width: Largura máxima do thumbnail (padrão 300).
        quality: Qualidade JPEG (padrão 75 — bom equilíbrio).

    Returns:
        Bytes do thumbnail em JPEG.

    Raises:
        PIL.UnidentifiedImageError: Se os bytes não forem imagem válida.
    """
    with Image.open(io.BytesIO(image_bytes)) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
