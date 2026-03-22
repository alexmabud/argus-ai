"""Script para gerar ícones PWA do Argus AI a partir da imagem do olho cyberpunk.

Processa a imagem original removendo o fundo branco e substituindo
pelo fundo escuro do app (#050A0F), depois redimensiona para os
tamanhos exigidos pelo manifest.json.
"""

from pathlib import Path

import numpy as np
from PIL import Image

SOURCE = Path(r"C:\Users\User\Downloads\Phone Link\1772505697458.png")
OUT_DIR = Path(__file__).parent.parent / "frontend" / "icons"
BG_COLOR = (5, 10, 15)  # #050A0F


def remove_white_bg(img: Image.Image) -> Image.Image:
    """Remove o fundo branco e substitui pelo fundo escuro do app.

    Args:
        img: Imagem original em qualquer modo.

    Returns:
        Imagem RGBA com fundo branco substituído por #050A0F.
    """
    img = img.convert("RGBA")
    data = np.array(img)

    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    mask = (r > 200) & (g > 200) & (b > 200)

    data[mask] = [*BG_COLOR, 255]
    return Image.fromarray(data, "RGBA")


def crop_square(img: Image.Image) -> Image.Image:
    """Faz crop quadrado centralizado na imagem.

    Args:
        img: Imagem de entrada.

    Returns:
        Imagem quadrada centralizada.
    """
    w, h = img.size
    size = min(w, h)
    left = (w - size) // 2
    top = (h - size) // 2
    return img.crop((left, top, left + size, top + size))


def generate(source: Path, out_dir: Path) -> None:
    """Gera icon-192.png e icon-512.png a partir da imagem fonte.

    Args:
        source: Caminho da imagem original do olho cyberpunk.
        out_dir: Diretório de saída (frontend/icons/).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(source)
    img = remove_white_bg(img)
    img = crop_square(img)

    for size in (512, 192):
        resized = img.resize((size, size), Image.LANCZOS)
        # Converter para RGB antes de salvar (remove canal alpha)
        final = Image.new("RGB", (size, size), BG_COLOR)
        final.paste(resized, mask=resized.split()[3])
        out_path = out_dir / f"icon-{size}.png"
        final.save(out_path, "PNG", optimize=True)
        print(f"Gerado: {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    generate(SOURCE, OUT_DIR)
