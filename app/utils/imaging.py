"""Utilitários de processamento de imagem (geração de thumbnails).

Usado por FotoService para gerar versão reduzida (~25KB) de fotos
de pessoas e abordagens, servida em listagens. Reduz drasticamente
tráfego do proxy /storage quando há muitas fotos por tela.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

# Registra o decoder HEIF/HEIC no Pillow para que thumbnails e marca d'água
# consigam abrir fotos de iPhone diretamente, sem depender de outro módulo
# tê-lo registrado antes (a marca d'água roda no proxy /storage, fora do
# fluxo de upload). Idempotente — registrar duas vezes é inofensivo.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - ambiente sem pillow-heif
    pass


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


def burn_watermark(
    image_bytes: bytes,
    matricula: str,
    *,
    opacity: int = 34,
    angle: int = 30,
) -> bytes:
    """Queima uma marca d'água diagonal com a matrícula nos pixels da imagem.

    Compõe um padrão de tile diagonal repetindo a matrícula sobre a imagem
    original, em baixa opacidade, e devolve os bytes preservando formato e
    dimensões. Aplica ``exif_transpose`` antes para não girar fotos de celular.
    A saída é determinística para o mesmo ``(image_bytes, matricula)`` — pré-
    requisito do cache por ``(asset, matrícula)``.

    Args:
        image_bytes: Bytes da imagem original (JPEG, PNG, WEBP).
        matricula: Matrícula do usuário autenticado (vinda da sessão).
        opacity: Alpha do texto (0-255). Padrão ~13%.
        angle: Ângulo do tile diagonal em graus.

    Returns:
        Bytes da imagem marcada, no mesmo formato da entrada.

    Raises:
        PIL.UnidentifiedImageError: Se ``image_bytes`` não for imagem válida
            (usado como sniff: o chamador trata como conteúdo não-marcável).
    """
    with Image.open(io.BytesIO(image_bytes)) as src:
        original_format = (src.format or "PNG").upper()
        base = ImageOps.exif_transpose(src).convert("RGBA")

    width, height = base.size
    font_size = max(13, width // 24)
    font = ImageFont.load_default(size=font_size)

    # Tile oversize para permitir rotação sem bordas vazias, depois recorta ao centro.
    diag = int((width**2 + height**2) ** 0.5)
    layer = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    label = f"{matricula} · ARGUS"
    # Espaçamento horizontal acompanha a largura do texto p/ não sobrepor o tile.
    text_w = int(draw.textlength(label, font=font))
    step_x = max(text_w + font_size * 3, 160)
    step_y = max(font_size * 5, 90)
    for y in range(0, diag, step_y):
        for x in range(0, diag, step_x):
            draw.text(
                (x, y),
                label,
                font=font,
                fill=(255, 255, 255, opacity),
                stroke_width=1,
                stroke_fill=(0, 0, 0, opacity),
            )

    layer = layer.rotate(angle, expand=False)
    left = (diag - width) // 2
    top = (diag - height) // 2
    layer = layer.crop((left, top, left + width, top + height))

    composited = Image.alpha_composite(base, layer)

    out = io.BytesIO()
    if original_format in ("JPEG", "JPG", "HEIF", "HEIC"):
        # HEIC/HEIF é servido como image/jpeg (browsers não exibem HEIC nativo),
        # então re-codifica em JPEG — também evita PNG gigante de foto de iPhone.
        composited.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
    elif original_format == "WEBP":
        composited.save(out, format="WEBP", quality=85)
    else:
        composited.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
