# HEIC → JPEG Conversion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Aceitar uploads HEIC/HEIF (iPhone) e convertê-los automaticamente para JPEG antes de salvar.

**Architecture:** A conversão ocorre no backend, em `upload_validation.py`, antes do upload ao storage. O `pillow-heif` registra suporte HEIC no Pillow via plugin. Os dois endpoints de foto que validam content_type são atualizados para aceitar `image/heic` e `image/heif`.

**Tech Stack:** `pillow-heif`, `Pillow` (já instalado), FastAPI, `app/core/upload_validation.py`, `app/api/v1/fotos.py`

---

### Task 1: Adicionar dependência `pillow-heif`

**Files:**
- Modify: `pyproject.toml`

**Step 1: Adicionar pillow-heif às dependências**

No `pyproject.toml`, na lista de dependências onde já existe `"pillow>=10.0.0"`, adicionar logo abaixo:

```toml
"pillow-heif>=0.18.0",
```

**Step 2: Instalar localmente**

```bash
pip install pillow-heif
```

Expected: instala sem erros.

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build(deps): adicionar pillow-heif para suporte a HEIC"
```

---

### Task 2: Função de conversão + magic bytes HEIC

**Files:**
- Modify: `app/core/upload_validation.py`
- Test: `tests/unit/test_upload_validation.py` (criar)

**Step 1: Escrever o teste com imagem HEIC fake**

Criar `tests/unit/test_upload_validation.py`:

```python
"""Testes para upload_validation: magic bytes e conversão HEIC."""

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestValidarMagicBytesImagem:
    """Testes para validar_magic_bytes_imagem."""

    def test_aceita_jpeg(self):
        """Deve aceitar magic bytes JPEG."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        validar_magic_bytes_imagem(b"\xff\xd8\xff" + b"\x00" * 10)

    def test_aceita_png(self):
        """Deve aceitar magic bytes PNG."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        validar_magic_bytes_imagem(b"\x89PNG" + b"\x00" * 10)

    def test_aceita_webp(self):
        """Deve aceitar magic bytes WebP."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        validar_magic_bytes_imagem(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 2)

    def test_aceita_heic(self):
        """Deve aceitar magic bytes HEIC (ftyp heic)."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        heic_bytes = b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 10
        validar_magic_bytes_imagem(heic_bytes)

    def test_aceita_heif_mif1(self):
        """Deve aceitar magic bytes HEIF (ftyp mif1)."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        heif_bytes = b"\x00\x00\x00\x18ftypMIF1" + b"\x00" * 10
        validar_magic_bytes_imagem(heif_bytes)

    def test_rejeita_executavel(self):
        """Deve rejeitar arquivo que não é imagem."""
        from app.core.upload_validation import validar_magic_bytes_imagem
        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(b"MZ\x00\x00" + b"\x00" * 10)
        assert exc.value.status_code == 400


class TestConverterHeicParaJpeg:
    """Testes para converter_heic_para_jpeg."""

    def test_retorna_jpeg(self):
        """Deve retornar bytes JPEG válidos após conversão."""
        from app.core.upload_validation import converter_heic_para_jpeg

        # Mock do pillow_heif e PIL
        fake_img = MagicMock()
        fake_img.convert.return_value = fake_img

        def fake_save(buf, format, quality):
            buf.write(b"\xff\xd8\xff" + b"\x00" * 10)

        fake_img.save.side_effect = fake_save

        with patch("app.core.upload_validation.pillow_heif") as mock_heif, \
             patch("app.core.upload_validation.Image") as mock_pil:
            mock_pil.open.return_value = fake_img
            result = converter_heic_para_jpeg(b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 50)

        assert result[:3] == b"\xff\xd8\xff"
```

**Step 2: Rodar para confirmar falha**

```bash
pytest tests/unit/test_upload_validation.py -v
```

Expected: FAIL — `converter_heic_para_jpeg` não existe ainda, e `validar_magic_bytes_imagem` rejeita HEIC.

**Step 3: Implementar em `upload_validation.py`**

Adicionar imports no topo do arquivo:

```python
from io import BytesIO

from PIL import Image

try:
    import pillow_heif
    _HEIF_AVAILABLE = True
except ImportError:
    _HEIF_AVAILABLE = False
```

Adicionar magic bytes HEIC na função `validar_magic_bytes_imagem`, antes do `raise` final:

```python
    # HEIC/HEIF: bytes 4-7 contêm "ftyp"
    if file_bytes[4:8] == b"ftyp":
        return
```

Adicionar a nova função após `validar_magic_bytes_imagem`:

```python
def converter_heic_para_jpeg(file_bytes: bytes) -> bytes:
    """Converte imagem HEIC/HEIF para JPEG.

    Usa pillow-heif para decodificar o container HEIC e re-salva
    como JPEG com qualidade 90. Chamada apenas quando o arquivo
    é detectado como HEIC/HEIF.

    Args:
        file_bytes: Bytes do arquivo HEIC/HEIF.

    Returns:
        Bytes do arquivo convertido em JPEG.

    Raises:
        HTTPException: 400 se pillow-heif não estiver disponível ou
            se a conversão falhar.
    """
    if not _HEIF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato HEIC não suportado neste servidor",
        )
    try:
        pillow_heif.register_heif_opener()
        img = Image.open(BytesIO(file_bytes)).convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao converter imagem HEIC",
        ) from exc
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_upload_validation.py -v
```

Expected: todos PASS.

**Step 5: Commit**

```bash
git add app/core/upload_validation.py tests/unit/test_upload_validation.py
git commit -m "feat(upload): adicionar suporte a HEIC com conversão automática para JPEG"
```

---

### Task 3: Aceitar HEIC nos endpoints de fotos

**Files:**
- Modify: `app/api/v1/fotos.py:39` e trechos dos dois endpoints

**Step 1: Atualizar `ALLOWED_IMAGE_MIMES`**

Localizar linha 39 em `app/api/v1/fotos.py`:

```python
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
```

Substituir por:

```python
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
```

**Step 2: Importar a função de conversão**

No bloco de imports de `app/api/v1/fotos.py`, adicionar `converter_heic_para_jpeg` ao import existente de `upload_validation`:

```python
from app.core.upload_validation import (
    converter_heic_para_jpeg,
    ler_upload_com_limite,
    validar_magic_bytes_imagem,
)
```

**Step 3: Adicionar conversão no endpoint `/upload`**

Após `validar_magic_bytes_imagem(file_bytes)` (linha ~105), adicionar:

```python
    # Converte HEIC/HEIF para JPEG antes de prosseguir
    original_content_type = file.content_type or "image/jpeg"
    if original_content_type in {"image/heic", "image/heif"}:
        file_bytes = converter_heic_para_jpeg(file_bytes)
        original_content_type = "image/jpeg"
```

E na chamada a `service.upload_foto`, trocar `content_type=file.content_type or "image/jpeg"` por `content_type=original_content_type`.

Também ajustar o filename para trocar extensão `.heic`/`.heif` por `.jpg`:

```python
    filename = file.filename or "foto.jpg"
    if filename.lower().endswith((".heic", ".heif")):
        filename = filename.rsplit(".", 1)[0] + ".jpg"
```

**Step 4: Adicionar conversão no endpoint de OCR (linha ~302)**

Mesmo padrão — após `validar_magic_bytes_imagem(file_bytes)`:

```python
    if (file.content_type or "") in {"image/heic", "image/heif"}:
        file_bytes = converter_heic_para_jpeg(file_bytes)
```

**Step 5: Rodar testes existentes**

```bash
pytest tests/ -v --tb=short
```

Expected: sem regressões.

**Step 6: Commit**

```bash
git add app/api/v1/fotos.py
git commit -m "feat(fotos): aceitar upload HEIC e converter para JPEG automaticamente"
```

---

### Task 4: Atualizar Dockerfile para garantir pillow-heif instalado

**Files:**
- Modify: `Dockerfile` (ou `Dockerfile.prod` se existir)

**Step 1: Verificar se há dependências de sistema para libheif**

`pillow-heif` >= 0.10 usa wheels pré-compilados no Linux — não requer `libheif` instalada separadamente na maioria dos casos. Verificar se o Dockerfile usa imagem `python:3.11-slim` ou similar.

Se o Dockerfile usa `pip install` a partir de `pyproject.toml` ou `requirements`, nada precisa mudar além do `pyproject.toml` já atualizado na Task 1.

Se houver um `requirements.txt` gerado separadamente, executar:

```bash
pip freeze | grep pillow
```

E garantir que `pillow-heif` aparece no arquivo de lock usado pelo Docker.

**Step 2: Build de teste local**

```bash
docker compose build api
```

Expected: build sem erros.

**Step 3: Commit (se houve mudança)**

```bash
git add Dockerfile  # ou Dockerfile.prod
git commit -m "build(docker): garantir pillow-heif na imagem"
```
