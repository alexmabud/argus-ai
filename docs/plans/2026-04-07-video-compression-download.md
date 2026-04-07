# Video Compression + Download Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprimir vídeos automaticamente após upload (arq worker + ffmpeg) e adicionar endpoint de download forçado de mídias/PDFs.

**Architecture:** Upload salva original no MinIO e enfileira job arq. Worker baixa bytes, roda ffmpeg H.264 via subprocess, substitui no MinIO. Endpoint `GET /fotos/{id}/download` busca Foto no banco (valida tenant), baixa bytes do MinIO, retorna StreamingResponse com `Content-Disposition: attachment`.

**Tech Stack:** Python 3.11 + FastAPI + arq + asyncio.subprocess (ffmpeg) + aioboto3 + SQLAlchemy async + Alembic

---

### Task 1: Adicionar ffmpeg ao Dockerfile

**Files:**
- Modify: `Dockerfile:5-13`

**Step 1: Editar Dockerfile**

Adicionar `ffmpeg` à lista de pacotes do `apt-get install`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-por \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

**Step 2: Verificar que o arquivo ficou correto**

```bash
grep ffmpeg Dockerfile
```
Expected: `    ffmpeg \`

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "chore(docker): adicionar ffmpeg para compressão de vídeo"
```

---

### Task 2: Adicionar campo `compressao_status` ao model Foto

**Files:**
- Modify: `app/models/foto.py`
- Test: `tests/unit/test_foto_service.py` (verificar campo existe)

**Step 1: Escrever o teste**

Abrir `tests/unit/test_foto_service.py` e adicionar no final:

```python
class TestFotoComCompressaoStatus:
    """Testa que Foto possui campo compressao_status."""

    def test_foto_tem_campo_compressao_status(self):
        """Foto deve ter atributo compressao_status com default 'na'."""
        from app.models.foto import Foto
        foto = Foto()
        assert hasattr(foto, "compressao_status")
        assert foto.compressao_status == "na"
```

**Step 2: Rodar o teste — deve falhar**

```bash
pytest tests/unit/test_foto_service.py::TestFotoComCompressaoStatus -v
```
Expected: FAIL — `AssertionError: assert False` (campo não existe ainda)

**Step 3: Adicionar campo ao model**

Em `app/models/foto.py`, adicionar após `face_processada`:

```python
compressao_status: Mapped[str] = mapped_column(
    String(10), default="na", server_default="na"
)
```

E atualizar a docstring da classe — adicionar nos Attributes:
```
compressao_status: Estado da compressão de vídeo ('na', 'pending', 'done', 'error').
```

**Step 4: Rodar o teste — deve passar**

```bash
pytest tests/unit/test_foto_service.py::TestFotoComCompressaoStatus -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/models/foto.py tests/unit/test_foto_service.py
git commit -m "feat(models): adicionar campo compressao_status em Foto"
```

---

### Task 3: Criar migration Alembic para `compressao_status`

**Files:**
- Create: `alembic/versions/<hash>_add_compressao_status_to_fotos.py` (gerado automaticamente)

**Step 1: Gerar migration**

```bash
make migrate-create msg="add-compressao-status-to-fotos"
```

**Step 2: Verificar migration gerada**

Abrir o arquivo gerado em `alembic/versions/` e confirmar que contém:

```python
def upgrade() -> None:
    op.add_column('fotos', sa.Column('compressao_status', sa.String(length=10), server_default='na', nullable=False))

def downgrade() -> None:
    op.drop_column('fotos', 'compressao_status')
```

Se o autogenerate não gerou corretamente (às vezes pgvector confunde o diff), edite manualmente o arquivo para ter exatamente esse conteúdo.

**Step 3: Aplicar migration**

```bash
make migrate
```
Expected: `Running upgrade ... -> <hash>, add-compressao-status-to-fotos`

**Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(migration): adicionar compressao_status na tabela fotos"
```

---

### Task 4: Criar `app/tasks/video_processor.py`

**Files:**
- Create: `app/tasks/video_processor.py`
- Create: `tests/unit/test_video_processor.py`

**Step 1: Escrever os testes**

Criar `tests/unit/test_video_processor.py`:

```python
"""Testes unitários para processamento de vídeo."""

import pytest


class TestDetectarVideo:
    """Testes para detecção de MIME types de vídeo."""

    def test_mp4_e_video(self):
        """video/mp4 deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video
        assert _e_video("video/mp4") is True

    def test_quicktime_e_video(self):
        """video/quicktime deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video
        assert _e_video("video/quicktime") is True

    def test_webm_e_video(self):
        """video/webm deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video
        assert _e_video("video/webm") is True

    def test_imagem_nao_e_video(self):
        """image/jpeg não deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video
        assert _e_video("image/jpeg") is False

    def test_pdf_nao_e_video(self):
        """application/pdf não deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video
        assert _e_video("application/pdf") is False


class TestComprimir:
    """Testes para compressão de vídeo via ffmpeg."""

    @pytest.mark.asyncio
    async def test_comprimir_retorna_bytes(self, tmp_path):
        """_comprimir_video deve retornar bytes menores que o input."""
        import subprocess
        # Criar vídeo de teste válido com ffmpeg
        video_path = tmp_path / "test.mp4"
        result = subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
            "-c:v", "libx264", "-t", "2", str(video_path), "-y"
        ], capture_output=True)
        if result.returncode != 0:
            pytest.skip("ffmpeg não disponível no ambiente de teste")

        video_bytes = video_path.read_bytes()
        from app.tasks.video_processor import _comprimir_video_sincrono
        compressed = _comprimir_video_sincrono(video_bytes)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
```

**Step 2: Rodar os testes — devem falhar**

```bash
pytest tests/unit/test_video_processor.py -v
```
Expected: FAIL — `ImportError: cannot import name '_e_video'`

**Step 3: Criar `app/tasks/video_processor.py`**

```python
"""Task de compressão de vídeo via ffmpeg.

Processa vídeos enviados para mídias de abordagem: download do MinIO,
compressão H.264 com ffmpeg (720p, CRF 28, preset fast), substituição
no MinIO e atualização do status no banco.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from app.services.storage_service import StorageService
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")

#: MIME types que identificam vídeos para compressão.
_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}


def _e_video(content_type: str) -> bool:
    """Verifica se o MIME type corresponde a um vídeo.

    Args:
        content_type: MIME type do arquivo.

    Returns:
        True se for vídeo, False caso contrário.
    """
    return content_type in _VIDEO_MIMES


def _comprimir_video_sincrono(video_bytes: bytes) -> bytes:
    """Comprime vídeo com ffmpeg: H.264, 720p max, CRF 28, preset fast.

    Executa ffmpeg via subprocess. Usa arquivos temporários para entrada
    e saída (ffmpeg não aceita stdin/stdout para MP4 sem -movflags).

    Args:
        video_bytes: Bytes do vídeo original.

    Returns:
        Bytes do vídeo comprimido em MP4/H.264.

    Raises:
        RuntimeError: Se ffmpeg falhar ou retornar arquivo vazio.
    """
    import subprocess

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        entrada = tmp / "input.mp4"
        saida = tmp / "output.mp4"

        entrada.write_bytes(video_bytes)

        cmd = [
            "ffmpeg",
            "-i", str(entrada),
            "-vf", "scale='if(gt(iw,1280),1280,iw)':'if(gt(ih,720),720,ih)':flags=lanczos",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            str(saida),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"ffmpeg falhou (código {result.returncode}): {stderr[-500:]}")

        compressed = saida.read_bytes()
        if not compressed:
            raise RuntimeError("ffmpeg produziu arquivo vazio")

        return compressed


async def comprimir_video_task(ctx: dict, foto_id: int) -> dict:
    """Task arq para comprimir vídeo de mídia de abordagem.

    Pipeline:
    1. Busca Foto no banco
    2. Download dos bytes do MinIO
    3. Comprime com ffmpeg em thread separada
    4. Substitui o arquivo no MinIO
    5. Atualiza compressao_status='done' no banco

    Args:
        ctx: Contexto do worker arq com db_session_factory.
        foto_id: ID da Foto a comprimir.

    Returns:
        Dicionário com status e métricas de compressão.
    """
    from sqlalchemy import select

    from app.models.foto import Foto

    db_factory = ctx["db_session_factory"]
    storage = StorageService()

    logger.info("Comprimindo vídeo da foto %d", foto_id)

    async with db_factory() as db:
        try:
            result = await db.execute(
                select(Foto)
                .where(Foto.id == foto_id)
                .with_for_update(skip_locked=True)
            )
            foto = result.scalar_one_or_none()

            if foto is None:
                logger.error("Foto %d não encontrada para compressão", foto_id)
                return {"status": "erro", "motivo": "Foto não encontrada"}

            if foto.compressao_status == "done":
                logger.info("Foto %d já comprimida, pulando", foto_id)
                return {"status": "já_comprimida"}

            # Download do original
            key = extrair_key_da_url(foto.arquivo_url)
            video_bytes = await storage.download(key)
            tamanho_original = len(video_bytes)

            # Compressão em thread separada (CPU-bound + subprocess)
            compressed = await asyncio.to_thread(_comprimir_video_sincrono, video_bytes)
            tamanho_comprimido = len(compressed)

            # Substituir no MinIO (mesma key)
            await storage.upload(compressed, key, "video/mp4")

            # Atualizar status no banco
            foto.compressao_status = "done"
            await db.commit()

            reducao_pct = round((1 - tamanho_comprimido / tamanho_original) * 100, 1)
            logger.info(
                "Foto %d comprimida: %d KB → %d KB (-%s%%)",
                foto_id,
                tamanho_original // 1024,
                tamanho_comprimido // 1024,
                reducao_pct,
            )
            return {
                "status": "sucesso",
                "tamanho_original_kb": tamanho_original // 1024,
                "tamanho_comprimido_kb": tamanho_comprimido // 1024,
                "reducao_pct": reducao_pct,
            }

        except Exception:
            await db.rollback()
            # Marcar como erro sem perder o arquivo original
            try:
                async with db_factory() as db2:
                    result2 = await db2.execute(select(Foto).where(Foto.id == foto_id))
                    foto2 = result2.scalar_one_or_none()
                    if foto2:
                        foto2.compressao_status = "error"
                        await db2.commit()
            except Exception:
                pass
            logger.exception("Erro ao comprimir vídeo da foto %d", foto_id)
            return {"status": "erro", "motivo": "Erro na compressão"}
```

**Step 4: Rodar os testes — devem passar**

```bash
pytest tests/unit/test_video_processor.py -v
```
Expected: PASS (o teste de `_comprimir_video_sincrono` será SKIP se ffmpeg não estiver no ambiente de CI — isso é esperado)

**Step 5: Commit**

```bash
git add app/tasks/video_processor.py tests/unit/test_video_processor.py
git commit -m "feat(tasks): criar task arq de compressão de vídeo com ffmpeg"
```

---

### Task 5: Registrar task no worker

**Files:**
- Modify: `app/worker.py`

**Step 1: Editar `app/worker.py`**

Adicionar import no topo (após `from app.tasks.pdf_processor import processar_pdf_task`):

```python
from app.tasks.video_processor import comprimir_video_task
```

Atualizar a lista `functions` em `WorkerSettings`:

```python
functions = [processar_pdf_task, processar_face_task, comprimir_video_task]
```

Atualizar também a docstring do módulo para incluir "compressão de vídeo":

```python
"""Worker arq para processamento assíncrono de tarefas pesadas.

Configura e executa o worker arq com Redis como broker de mensagens.
Registra tasks de processamento de PDF (OCR + extração de texto),
processamento facial (InsightFace) e compressão de vídeo (ffmpeg).
...
```

**Step 2: Verificar que o worker importa sem erro**

```bash
python -c "from app.worker import WorkerSettings; print(WorkerSettings.functions)"
```
Expected: lista com 3 funções incluindo `comprimir_video_task`

**Step 3: Commit**

```bash
git add app/worker.py
git commit -m "feat(worker): registrar comprimir_video_task no arq"
```

---

### Task 6: Enfileirar compressão após upload de vídeo

**Files:**
- Modify: `app/api/v1/fotos.py:383-434` (endpoint `upload_midia_abordagem`)
- Test: `tests/unit/test_upload_validation.py` (verificar helper `_e_video` é importável)

**Step 1: Escrever teste de integração (mock)**

Criar `tests/unit/test_fotos_router.py`:

```python
"""Testes para o router de fotos — enfileiramento de compressão."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestUploadMidiaEnfileira:
    """Verifica que upload de vídeo enfileira compressão."""

    def test_e_video_mp4(self):
        """_e_video deve retornar True para video/mp4."""
        from app.tasks.video_processor import _e_video
        assert _e_video("video/mp4") is True

    def test_e_video_imagem_false(self):
        """_e_video deve retornar False para image/jpeg."""
        from app.tasks.video_processor import _e_video
        assert _e_video("image/jpeg") is False
```

**Step 2: Rodar teste**

```bash
pytest tests/unit/test_fotos_router.py -v
```
Expected: PASS

**Step 3: Modificar o endpoint `upload_midia_abordagem`**

Em `app/api/v1/fotos.py`, após a linha `foto = await service.upload_foto(...)` dentro do bloco `try` do endpoint `upload_midia_abordagem` (por volta da linha 403), adicionar antes do `except`:

```python
        # Enfileirar compressão de vídeo em background
        if content_type.startswith("video/"):
            foto.compressao_status = "pending"
            await db.commit()
            try:
                from arq.connections import ArqRedis, create_pool

                from app.worker import WorkerSettings

                redis_pool: ArqRedis = await create_pool(WorkerSettings.redis_settings)
                await redis_pool.enqueue_job("comprimir_video_task", foto.id)
                await redis_pool.aclose()
            except Exception:
                logger.warning(
                    "Worker offline — vídeo da foto %d será comprimido depois", foto.id
                )
```

E adicionar o import de `_e_video` no topo do arquivo (não é necessário já que usamos `content_type.startswith("video/")`).

**Step 4: Rodar testes existentes para garantir nada quebrou**

```bash
pytest tests/unit/test_upload_validation.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/v1/fotos.py tests/unit/test_fotos_router.py
git commit -m "feat(api): enfileirar compressão de vídeo após upload de mídia"
```

---

### Task 7: Endpoint de download forçado `GET /fotos/{foto_id}/download`

**Files:**
- Modify: `app/api/v1/fotos.py`
- Create: `tests/unit/test_download_endpoint.py`

**Step 1: Escrever testes**

Criar `tests/unit/test_download_endpoint.py`:

```python
"""Testes para o endpoint de download de mídia."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSanitizarFilename:
    """Testa sanitização de nomes de arquivo para Content-Disposition."""

    def test_filename_simples(self):
        """Filename simples não deve ser alterado."""
        from app.api.v1.fotos import _sanitizar_filename
        assert _sanitizar_filename("video.mp4") == "video.mp4"

    def test_filename_com_path_traversal(self):
        """Path traversal deve ser removido."""
        from app.api.v1.fotos import _sanitizar_filename
        result = _sanitizar_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_filename_vazio_retorna_default(self):
        """Filename vazio deve retornar 'midia'."""
        from app.api.v1.fotos import _sanitizar_filename
        assert _sanitizar_filename("") == "midia"

    def test_filename_com_espacos(self):
        """Espaços no filename devem ser substituídos por underscore."""
        from app.api.v1.fotos import _sanitizar_filename
        result = _sanitizar_filename("meu video da abordagem.mp4")
        assert " " not in result
```

**Step 2: Rodar testes — devem falhar**

```bash
pytest tests/unit/test_download_endpoint.py -v
```
Expected: FAIL — `ImportError: cannot import name '_sanitizar_filename'`

**Step 3: Adicionar função auxiliar e endpoint em `app/api/v1/fotos.py`**

Adicionar imports no topo do arquivo (junto aos existentes):

```python
import re

from fastapi.responses import StreamingResponse
```

Adicionar função auxiliar antes do router:

```python
def _sanitizar_filename(filename: str) -> str:
    """Sanitiza nome de arquivo para uso em Content-Disposition.

    Remove path traversal, substitui espaços por underscore e
    garante que o resultado não seja vazio.

    Args:
        filename: Nome original do arquivo.

    Returns:
        Nome sanitizado seguro para cabeçalho HTTP.
    """
    # Remover qualquer componente de path
    name = filename.replace("\\", "/").split("/")[-1]
    # Substituir espaços por underscore
    name = name.replace(" ", "_")
    # Remover caracteres não seguros (manter alfanuméricos, ponto, hífen, underscore)
    name = re.sub(r"[^\w.\-]", "", name)
    return name or "midia"
```

Adicionar endpoint ao final do router (antes do último fechamento):

```python
@router.get("/{foto_id}/download")
@limiter.limit("30/minute")
async def download_midia(
    request: Request,
    foto_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> StreamingResponse:
    """Faz download forçado de mídia ou PDF vinculado a uma abordagem.

    Busca a Foto no banco, valida que pertence à guarnição do usuário,
    baixa os bytes do MinIO e retorna com Content-Disposition: attachment
    para forçar o download no browser.

    Args:
        request: Objeto Request do FastAPI.
        foto_id: ID da Foto a baixar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        StreamingResponse com o arquivo e header de download.

    Raises:
        HTTPException 404: Foto não encontrada ou deletada.
        HTTPException 403: Foto não pertence à guarnição do usuário.
        HTTPException 500: Erro ao baixar do storage.

    Status Code:
        200: Arquivo retornado.
        429: Rate limit (30/min).
    """
    from sqlalchemy import select

    from app.models.foto import Foto

    # Buscar foto (respeitando soft delete via ativo=True)
    result = await db.execute(
        select(Foto).where(Foto.id == foto_id, Foto.ativo == True)  # noqa: E712
    )
    foto = result.scalar_one_or_none()

    if foto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada")

    # Validar tenant
    if foto.guarnicao_id is not None and foto.guarnicao_id != user.guarnicao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta mídia",
        )

    # Determinar nome do arquivo a partir da URL
    url_filename = foto.arquivo_url.split("/")[-1]
    safe_filename = _sanitizar_filename(url_filename)

    # Determinar content-type a partir da extensão
    ext = safe_filename.rsplit(".", 1)[-1].lower() if "." in safe_filename else ""
    content_type_map = {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "avi": "video/x-msvideo",
        "webm": "video/webm",
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    media_type = content_type_map.get(ext, "application/octet-stream")

    # Download do MinIO
    from app.utils.s3 import extrair_key_da_url

    try:
        storage = StorageService()
        key = extrair_key_da_url(foto.arquivo_url)
        file_bytes = await storage.download(key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao baixar o arquivo do storage.",
        ) from exc

    return StreamingResponse(
        iter([file_bytes]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_download_endpoint.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/v1/fotos.py tests/unit/test_download_endpoint.py
git commit -m "feat(api): adicionar endpoint de download forçado de mídias e PDFs"
```

---

### Task 8: Botão de download no frontend — abordagem-detalhe

**Files:**
- Modify: `frontend/js/pages/abordagem-detalhe.js:204-217` (template do loop de mídias)

**Step 1: Localizar o template das mídias**

O loop de mídias está em torno da linha 204:
```html
<template x-for="f in midiasAbordagem" :key="f.id">
  <div style="width:64px;height:64px;..." @click="fotoAmpliada = f.arquivo_url">
```

**Step 2: Adicionar botão de download**

Substituir o `<div>` do loop de mídias para incluir botão de download no hover:

```html
<template x-for="f in midiasAbordagem" :key="f.id">
  <div style="width:64px;height:64px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:4px;overflow:hidden;cursor:pointer;position:relative;"
       @click="fotoAmpliada = f.arquivo_url">
    <template x-if="/\.(mp4|mov|avi|webm)/i.test(f.arquivo_url)">
      <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;">
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/></svg>
        <span style="font-family:var(--font-display);font-size:7px;color:var(--color-primary);">VID</span>
      </div>
    </template>
    <template x-if="!/\.(mp4|mov|avi|webm)/i.test(f.arquivo_url)">
      <img :src="f.arquivo_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
    </template>
    <!-- Botão download -->
    <a :href="`/api/v1/fotos/${f.id}/download`"
       @click.stop
       style="position:absolute;bottom:2px;right:2px;background:rgba(0,0,0,0.65);border-radius:3px;padding:2px;display:flex;align-items:center;justify-content:center;"
       title="Baixar">
      <svg width="12" height="12" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
    </a>
  </div>
</template>
```

**Step 3: Verificar visualmente**

Abrir o app localmente (`make dev`), navegar para uma abordagem com mídias e verificar que o ícone de download aparece no canto inferior direito de cada mídia.

**Step 4: Commit**

```bash
git add frontend/js/pages/abordagem-detalhe.js
git commit -m "feat(frontend): adicionar botão de download em mídias da abordagem"
```

---

### Task 9: Botão de download no frontend — ocorrências (PDF)

**Files:**
- Modify: `frontend/js/pages/ocorrencias.js`

**Step 1: Localizar onde PDFs são exibidos**

```bash
grep -n "arquivo_pdf\|ocorrencia\|pdf" frontend/js/pages/ocorrencias.js | head -20
```

**Step 2: Adicionar botão de download ao lado de cada ocorrência**

Localizar o template que exibe a ocorrência (buscar por `numero_ocorrencia` ou link para o PDF). Adicionar link de download:

```html
<a :href="`/api/v1/fotos/${oc.foto_id}/download`"
   style="font-family:var(--font-display);font-size:9px;color:var(--color-primary);text-decoration:none;display:inline-flex;align-items:center;gap:3px;"
   title="Baixar PDF">
  <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
  PDF
</a>
```

**Nota:** O endpoint `/ocorrencias/` retorna `arquivo_pdf_url` mas não um `foto_id` — verificar o schema de ocorrência. Se não tiver `foto_id`, usar `<a :href="oc.arquivo_pdf_url" download>` como alternativa (força download via atributo HTML nativo para URLs same-origin).

**Step 3: Commit**

```bash
git add frontend/js/pages/ocorrencias.js
git commit -m "feat(frontend): adicionar botão de download de PDF nas ocorrências"
```

---

### Task 10: Rodar suite completa de testes

**Step 1: Rodar todos os testes**

```bash
make test
```

**Step 2: Verificar que não há falhas**

Expected: todos os testes passam. Se `test_comprimir_video_sincrono` for SKIP (ffmpeg ausente no CI), é aceitável.

**Step 3: Rodar lint**

```bash
make lint
```

Expected: sem erros de ruff ou mypy.

**Step 4: Commit final se necessário**

Se houver ajustes de lint:
```bash
git add -p
git commit -m "fix(lint): ajustes de estilo após implementação de compressão de vídeo"
```

---

## Resumo das mudanças

| Arquivo | Tipo | O que muda |
|---|---|---|
| `Dockerfile` | Modify | `apt-get install ffmpeg` |
| `app/models/foto.py` | Modify | Campo `compressao_status` |
| `alembic/versions/...` | Create | Migration do campo |
| `app/tasks/video_processor.py` | Create | Task arq de compressão |
| `app/worker.py` | Modify | Registrar `comprimir_video_task` |
| `app/api/v1/fotos.py` | Modify | Enfileirar compressão + endpoint download |
| `frontend/js/pages/abordagem-detalhe.js` | Modify | Botão download por mídia |
| `frontend/js/pages/ocorrencias.js` | Modify | Botão download PDF |
| `tests/unit/test_video_processor.py` | Create | Testes do processor |
| `tests/unit/test_download_endpoint.py` | Create | Testes do endpoint download |
