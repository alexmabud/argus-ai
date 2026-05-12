# Otimização de Storage (Thumbnails + Proxy) — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para executar este plano tarefa-por-tarefa.

**Goal:** Reduzir em ~95% o tráfego e latência de listagens de abordagens com muitas fotos, mantendo 100% da auditoria atual (proxy autenticado).

**Architecture:** Quatro frentes complementares — (A) reaproveitar conexão S3, fazer streaming e ETag/304 no proxy; (B) gerar thumbnail JPEG 300px no upload e expor `thumbnail_url` nos schemas; (C) backfill de thumbs de fotos existentes via arq worker; (D) frontend usar `thumbnail_url` em listagens. Auditoria permanece centralizada no proxy `/storage/{path:path}` em [main.py:128](app/main.py#L128).

**Tech Stack:** FastAPI · aioboto3 · Pillow (já instalado) · arq · SQLAlchemy 2.0 async · Alembic · Alpine.js

**Ordem de execução:** Fase A → Fase B → Fase C → Fase D. Cada fase compila/passa em testes antes da próxima. Commits frequentes.

---

## Fase A — Proxy mais eficiente (sem mudança de schema)

Ganho independente de tudo. Não altera contrato com frontend. Pode ser feito sozinho e mergeado isolado.

### Task A1: Singleton de cliente S3 no lifespan da API

**Objetivo:** Eliminar o `async with self._session.client(...)` por request. Cliente S3 vive enquanto o processo viver, reaproveitando TCP/TLS keep-alive.

**Files:**
- Modify: `app/services/storage_service.py`
- Modify: `app/main.py` (lifespan)
- Modify: `app/worker.py` (startup do worker — mesma técnica)
- Test: `tests/unit/services/test_storage_service.py`

**Step 1: Escrever teste que comprove reuso de cliente**

Criar arquivo de teste (ou adicionar ao existente). Conteúdo:

```python
"""Testes do StorageService — singleton de cliente S3."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import storage_service as ss_module


@pytest.mark.asyncio
async def test_storage_service_reutiliza_cliente_entre_chamadas(monkeypatch):
    """O cliente S3 deve ser criado uma única vez e reusado."""
    fake_client = MagicMock()
    fake_client.get_object = AsyncMock(
        return_value={"Body": AsyncMock(read=AsyncMock(return_value=b"x")),
                       "ContentType": "image/jpeg"}
    )
    create_calls = {"n": 0}

    async def fake_aenter(self):
        create_calls["n"] += 1
        return fake_client

    async def fake_aexit(self, *a):
        return None

    monkeypatch.setattr(
        ss_module.aioboto3.Session, "client",
        lambda self, *a, **kw: type("CM", (), {"__aenter__": fake_aenter,
                                                "__aexit__": fake_aexit})(),
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
```

**Step 2: Rodar teste, confirmar falha**

```bash
cd /home/ser/Projetos/argus_ai
poetry run pytest tests/unit/services/test_storage_service.py::test_storage_service_reutiliza_cliente_entre_chamadas -v
```

Esperado: FAIL — `StorageService` ainda não tem `startup`/`shutdown` e cria client por chamada.

**Step 3: Refatorar `StorageService`**

Substituir o padrão atual por cliente persistente. Conteúdo de [app/services/storage_service.py](app/services/storage_service.py) (apenas a classe — preservar `normalize_storage_url` e regex no topo):

```python
class StorageService:
    """Serviço S3/R2 com cliente persistente (reusa TCP keep-alive).

    O cliente é criado em ``startup()`` (lifespan) e fechado em
    ``shutdown()``. Operações usam ``self._client`` diretamente,
    evitando handshake TCP/TLS por chamada.
    """

    _instance: "StorageService | None" = None

    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._client_ctx = None
        self._client = None

    @classmethod
    def get(cls) -> "StorageService":
        """Retorna a instância singleton (criada no lifespan)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def startup(self) -> None:
        """Abre cliente S3 persistente. Chamar no lifespan da app/worker."""
        if self._client is not None:
            return
        self._client_ctx = self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self._client = await self._client_ctx.__aenter__()

    async def shutdown(self) -> None:
        """Fecha cliente S3. Chamar no shutdown do lifespan."""
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client_ctx = None
            self._client = None

    def _ensure_client(self):
        if self._client is None:
            raise RuntimeError(
                "StorageService não inicializado — chame startup() no lifespan."
            )
        return self._client

    # Atualizar generate_key (mantém igual)
    def generate_key(self, prefix: str, filename: str) -> str:
        unique_id = uuid.uuid4().hex[:12]
        return f"{prefix}/{unique_id}_{filename}"

    async def upload(self, file_bytes: bytes, key: str,
                     content_type: str = "image/jpeg") -> str:
        client = self._ensure_client()
        await client.put_object(
            Bucket=settings.S3_BUCKET, Key=key,
            Body=file_bytes, ContentType=content_type,
        )
        logger.info("Upload concluído: %s", key)
        return f"/storage/{settings.S3_BUCKET}/{key}"

    async def delete(self, key: str) -> None:
        client = self._ensure_client()
        await client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
        logger.info("Arquivo removido: %s", key)

    async def download(self, key: str) -> bytes:
        body, _ = await self.download_with_meta(key)
        return body

    async def download_with_meta(self, key: str) -> tuple[bytes, str]:
        client = self._ensure_client()
        response = await client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        body = await response["Body"].read()
        content_type = response.get("ContentType") or "application/octet-stream"
        return body, content_type
```

**Step 4: Inicializar singleton no lifespan da API**

Em [app/main.py](app/main.py), localizar o `lifespan` context manager (procurar `@asynccontextmanager` ou `lifespan=`). Adicionar:

```python
from app.services.storage_service import StorageService

@asynccontextmanager
async def lifespan(app: FastAPI):
    await StorageService.get().startup()
    try:
        yield
    finally:
        await StorageService.get().shutdown()
```

Se o lifespan já existir com outras inicializações, integrar a chamada `startup()` no início e `shutdown()` no final.

**Step 5: Inicializar singleton no worker**

Em [app/worker.py:22-52](app/worker.py#L22-L52), dentro de `startup(ctx)`:

```python
from app.services.storage_service import StorageService

await StorageService.get().startup()
ctx["storage"] = StorageService.get()
```

E no `shutdown(ctx)`:

```python
await StorageService.get().shutdown()
```

**Step 6: Atualizar chamadores que faziam `StorageService()`**

Trocar `StorageService()` por `StorageService.get()` em:

- [app/services/foto_service.py:63](app/services/foto_service.py#L63)
- [app/main.py:161](app/main.py#L161)
- [app/api/v1/fotos.py:534](app/api/v1/fotos.py#L534) (download_midia)
- [app/tasks/face_processor.py:44](app/tasks/face_processor.py#L44)
- Qualquer outro lugar achado via `grep -rn "StorageService()" app/`

Rodar antes:
```bash
grep -rn "StorageService()" app/
```

**Step 7: Rodar testes**

```bash
poetry run pytest tests/unit/services/test_storage_service.py -v
poetry run pytest tests/ -x -q
```

Esperado: teste novo PASS; suíte completa sem regressões.

**Step 8: Commit**

```bash
git add app/services/storage_service.py app/main.py app/worker.py \
        app/services/foto_service.py app/api/v1/fotos.py \
        app/tasks/face_processor.py \
        tests/unit/services/test_storage_service.py
git commit -m "perf(storage): reaproveita cliente S3 entre requests (singleton no lifespan)"
```

---

### Task A2: StreamingResponse no proxy `/storage/*`

**Objetivo:** Não carregar arquivo inteiro na memória — começar a enviar bytes pro browser conforme chegam do R2.

**Files:**
- Modify: `app/services/storage_service.py` (novo método `stream_with_meta`)
- Modify: `app/main.py` (storage_proxy)
- Test: `tests/integration/test_storage_proxy.py` (criar se não existir)

**Step 1: Escrever teste que confirme StreamingResponse**

```python
"""Testes do proxy autenticado /storage/{path}."""

import pytest
from fastapi.responses import StreamingResponse

# Reusar fixtures de cliente autenticado já existentes no projeto.
# Buscar fixture análoga em tests/conftest.py: client autenticado.

@pytest.mark.asyncio
async def test_storage_proxy_retorna_streaming_response(authenticated_client, mock_s3):
    """Proxy /storage deve usar StreamingResponse, não Response."""
    # mock_s3 deve cobrir get_object retornando um Body com iter_chunks
    response = await authenticated_client.get("/storage/argus/fotos/x.jpg")
    assert response.status_code == 200
    assert "Content-Type" in response.headers
```

Nota: se não houver fixture `mock_s3` ou `authenticated_client`, verificar [tests/conftest.py](tests/conftest.py) e adaptar. Se a infra de mock de S3 não existir, pular este teste e rodar apenas teste unitário do método `stream_with_meta`.

**Step 2: Adicionar método `stream_with_meta` ao `StorageService`**

Em `app/services/storage_service.py`, adicionar:

```python
async def stream_with_meta(
    self, key: str, if_none_match: str | None = None,
) -> tuple[object, str, str | None, int | None]:
    """Abre stream do S3 sem materializar bytes em memória.

    Args:
        key: Chave do objeto.
        if_none_match: ETag enviado pelo cliente (cabeçalho If-None-Match).
            Se bater com o ETag do objeto, S3 retorna 304 (PreconditionFailed
            tratado pelo caller).

    Returns:
        Tupla (body_stream, content_type, etag, content_length).
        body_stream é o ``StreamingBody`` do aioboto3 — usar
        ``async for chunk in body_stream.iter_chunks(8192)``.

    Raises:
        ClientError: NoSuchKey, NotModified (304) ou outros erros S3.
    """
    client = self._ensure_client()
    kwargs = {"Bucket": settings.S3_BUCKET, "Key": key}
    if if_none_match:
        kwargs["IfNoneMatch"] = if_none_match
    response = await client.get_object(**kwargs)
    return (
        response["Body"],
        response.get("ContentType") or "application/octet-stream",
        response.get("ETag"),
        response.get("ContentLength"),
    )
```

**Step 3: Substituir o storage_proxy por versão com streaming + ETag**

Em [app/main.py:128-179](app/main.py#L128-L179), substituir o handler:

```python
from fastapi.responses import StreamingResponse

@app.get("/storage/{path:path}")
async def storage_proxy(
    path: str,
    request: Request,
    _: Usuario = Depends(get_current_user),
) -> Response:
    """Proxy autenticado para arquivos no storage S3/MinIO.

    Streama os bytes diretamente do S3 para o cliente, sem buffer
    intermediário. Suporta cache via ETag/If-None-Match: se o cliente
    enviar o mesmo ETag, o S3 retorna 304 nativamente e poupamos a
    transferência inteira.
    """
    bucket, _sep, key = path.partition("/")
    if not key or bucket != settings.S3_BUCKET:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if_none_match = request.headers.get("if-none-match")

    try:
        body, content_type, etag, length = (
            await StorageService.get().stream_with_meta(key, if_none_match=if_none_match)
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code == "304" or status_code == 304:
            return Response(status_code=304)
        if code in {"NoSuchKey", "404"} or status_code == 404:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado") from exc
        logger.exception("Falha ao baixar %s: %s", key, code)
        raise HTTPException(status_code=502, detail="Erro ao acessar storage") from exc

    headers = {
        "Content-Type": content_type,
        "Cache-Control": "private, max-age=3600",
    }
    if etag:
        headers["ETag"] = etag
    if length is not None:
        headers["Content-Length"] = str(length)

    async def chunks():
        async for chunk in body.iter_chunks(64 * 1024):
            yield chunk

    return StreamingResponse(chunks(), headers=headers, media_type=content_type)
```

**Step 4: Rodar testes**

```bash
poetry run pytest tests/integration/test_storage_proxy.py -v
poetry run pytest tests/ -x -q
```

**Step 5: Teste manual no browser (dev server)**

```bash
make dev
```

Abrir uma abordagem com fotos, conferir no DevTools:
- Network → tipo da resposta é `image/jpeg` com `Transfer-Encoding: chunked` ou `Content-Length` correto
- Header `ETag` presente
- F5 após 1h (ou ajustar max-age=0 temporariamente) → segunda request retorna 304

**Step 6: Commit**

```bash
git add app/services/storage_service.py app/main.py \
        tests/integration/test_storage_proxy.py
git commit -m "perf(storage): proxy /storage usa StreamingResponse + ETag/304"
```

---

## Fase B — Thumbnail no upload

### Task B1: Migration Alembic — colunas `thumbnail_url`

**Objetivo:** Adicionar campo `thumbnail_url` em `fotos` e `foto_principal_thumb_url` em `pessoas`.

**Files:**
- Create: `alembic/versions/<hash>_add_thumbnail_url.py`
- Modify: `app/models/foto.py`
- Modify: `app/models/pessoa.py`

**Step 1: Gerar migration**

```bash
cd /home/ser/Projetos/argus_ai
make migrate msg="add thumbnail_url em fotos e pessoas"
```

**Step 2: Editar a migration gerada**

Conteúdo do `upgrade()`:

```python
def upgrade() -> None:
    op.add_column(
        "fotos",
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "pessoas",
        sa.Column("foto_principal_thumb_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pessoas", "foto_principal_thumb_url")
    op.drop_column("fotos", "thumbnail_url")
```

**Step 3: Aplicar migration**

```bash
poetry run alembic upgrade head
```

Verificar:
```bash
poetry run alembic current
```

**Step 4: Atualizar modelos**

Em [app/models/foto.py:50](app/models/foto.py#L50), após `arquivo_url`, adicionar:

```python
thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

Atualizar docstring da classe — incluir `thumbnail_url` em `Attributes:`.

Em [app/models/pessoa.py](app/models/pessoa.py), localizar `foto_principal_url` e adicionar logo abaixo:

```python
foto_principal_thumb_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

Atualizar docstring com o novo campo.

**Step 5: Commit**

```bash
git add alembic/versions/*thumbnail_url*.py app/models/foto.py app/models/pessoa.py
git commit -m "feat(foto): adiciona thumbnail_url em fotos e pessoas (migration + model)"
```

---

### Task B2: Utilitário de geração de thumbnail

**Objetivo:** Função pura que recebe bytes JPEG/PNG/WEBP e retorna bytes da thumb 300px JPEG q75.

**Files:**
- Create: `app/utils/imaging.py`
- Test: `tests/unit/utils/test_imaging.py`

**Step 1: Escrever teste**

```python
"""Testes do gerador de thumbnails."""

import io

import pytest
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
```

**Step 2: Rodar teste**

```bash
poetry run pytest tests/unit/utils/test_imaging.py -v
```

Esperado: FAIL (módulo não existe).

**Step 3: Implementar `app/utils/imaging.py`**

```python
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
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
```

**Step 4: Rodar teste**

```bash
poetry run pytest tests/unit/utils/test_imaging.py -v
```

Esperado: 4 PASS.

**Step 5: Commit**

```bash
git add app/utils/imaging.py tests/unit/utils/test_imaging.py
git commit -m "feat(imaging): util gerar_thumbnail (300px JPEG q75) com correção EXIF"
```

---

### Task B3: `FotoService.upload_foto` gera e salva thumb

**Objetivo:** Toda foto nova entra no banco com `thumbnail_url` preenchido. Tipos não-imagem (PDF, vídeo) são puláveis.

**Files:**
- Modify: `app/services/foto_service.py`
- Modify: `app/services/storage_service.py` (nada novo — só usar)
- Test: `tests/unit/services/test_foto_service.py`

**Step 1: Escrever teste**

```python
@pytest.mark.asyncio
async def test_upload_foto_gera_thumbnail(db_session, mock_storage, monkeypatch):
    """Upload de imagem deve gerar e salvar thumbnail_url."""
    service = FotoService(db_session)
    img_bytes = _imagem_dummy(1200, 800)  # usar helper

    foto = await service.upload_foto(
        file_bytes=img_bytes,
        filename="abordagem.jpg",
        content_type="image/jpeg",
        pessoa_id=None,
        abordagem_id=1,
        veiculo_id=None,
        tipo="rosto",
        latitude=None,
        longitude=None,
        user_id=1,
    )

    assert foto.thumbnail_url is not None
    assert foto.thumbnail_url.startswith("/storage/")
    assert foto.thumbnail_url != foto.arquivo_url


@pytest.mark.asyncio
async def test_upload_pdf_nao_gera_thumbnail(db_session, mock_storage):
    """PDFs e vídeos não devem tentar gerar thumb."""
    service = FotoService(db_session)
    pdf_bytes = b"%PDF-1.4\n%fake"

    foto = await service.upload_foto(
        file_bytes=pdf_bytes,
        filename="auto.pdf",
        content_type="application/pdf",
        pessoa_id=None,
        abordagem_id=1,
        veiculo_id=None,
        tipo="midia_abordagem",
        latitude=None,
        longitude=None,
        user_id=1,
    )

    assert foto.thumbnail_url is None
```

**Step 2: Rodar teste**

```bash
poetry run pytest tests/unit/services/test_foto_service.py -v -k thumbnail
```

Esperado: FAIL.

**Step 3: Atualizar `FotoService.upload_foto`**

Em [app/services/foto_service.py:121-138](app/services/foto_service.py#L121-L138), substituir o bloco `# 1. Upload para S3/R2 ... # 2. Criar registro Foto no banco`:

```python
# 1. Upload da imagem original
key = self.storage.generate_key("fotos", filename)
url = await self.storage.upload(file_bytes, key, content_type)

# 1b. Gerar e enviar thumbnail (apenas para imagens — pula PDF/vídeo)
thumbnail_url: str | None = None
if content_type.startswith("image/"):
    try:
        from app.utils.imaging import gerar_thumbnail
        thumb_bytes = await asyncio.to_thread(gerar_thumbnail, file_bytes)
        thumb_filename = filename.rsplit(".", 1)[0] + "_thumb.jpg"
        thumb_key = self.storage.generate_key("thumbs", thumb_filename)
        thumbnail_url = await self.storage.upload(
            thumb_bytes, thumb_key, content_type="image/jpeg",
        )
    except Exception:
        # Thumb é otimização — falha não bloqueia o upload da foto.
        logger.warning("Falha ao gerar thumbnail para %s", key, exc_info=True)

# 2. Criar registro Foto no banco
foto = Foto(
    arquivo_url=url,
    thumbnail_url=thumbnail_url,
    tipo=tipo,
    ...
)
```

Adicionar import `logger` no topo do módulo se ainda não houver.

**Step 4: Atualizar bloco "foto principal" em fotos.py**

Em [app/api/v1/fotos.py:170-175](app/api/v1/fotos.py#L170-L175):

```python
if tipo == FotoTipo.rosto and pessoa_id:
    pessoa = await db.get(Pessoa, pessoa_id)
    if pessoa:
        pessoa.foto_principal_url = foto.arquivo_url
        pessoa.foto_principal_thumb_url = foto.thumbnail_url
        await db.commit()
```

**Step 5: Rodar testes**

```bash
poetry run pytest tests/unit/services/test_foto_service.py -v
poetry run pytest tests/ -x -q
```

**Step 6: Commit**

```bash
git add app/services/foto_service.py app/api/v1/fotos.py \
        tests/unit/services/test_foto_service.py
git commit -m "feat(foto): gera thumbnail no upload e atribui a pessoa.foto_principal_thumb_url"
```

---

### Task B4: Schemas expõem `thumbnail_url`

**Files:**
- Modify: `app/schemas/foto.py`
- Modify: `app/schemas/pessoa.py`

**Step 1: Atualizar `FotoRead`, `FotoUploadResponse`, `BuscaRostoItem`**

Em [app/schemas/foto.py:38-83](app/schemas/foto.py#L38-L83):

```python
class FotoRead(BaseModel):
    id: int
    arquivo_url: str
    thumbnail_url: str | None = None  # NOVO
    tipo: str
    data_hora: datetime
    latitude: float | None = None
    longitude: float | None = None
    pessoa_id: int | None = None
    abordagem_id: int | None = None
    veiculo_id: int | None = None
    face_processada: bool

    _normalize_url = field_validator(
        "arquivo_url", "thumbnail_url", mode="before"
    )(normalize_storage_url)

    model_config = {"from_attributes": True}


class FotoUploadResponse(BaseModel):
    id: int
    arquivo_url: str
    thumbnail_url: str | None = None  # NOVO
    tipo: str

    _normalize_url = field_validator(
        "arquivo_url", "thumbnail_url", mode="before"
    )(normalize_storage_url)


class BuscaRostoItem(BaseModel):
    foto_id: int
    arquivo_url: str
    thumbnail_url: str | None = None  # NOVO
    pessoa_id: int | None = None
    similaridade: float
    nome: str | None = None
    cpf_masked: str | None = None
    apelido: str | None = None
    foto_principal_url: str | None = None
    foto_principal_thumb_url: str | None = None  # NOVO

    _normalize_urls = field_validator(
        "arquivo_url", "thumbnail_url",
        "foto_principal_url", "foto_principal_thumb_url",
        mode="before",
    )(normalize_storage_url)

    model_config = {"from_attributes": True}
```

Atualizar docstrings (`Attributes:`) com os novos campos.

**Step 2: Atualizar [app/schemas/pessoa.py:87](app/schemas/pessoa.py#L87)**

Adicionar `foto_principal_thumb_url: str | None = None` ao lado de `foto_principal_url`, e adicionar o campo no validator existente:

```python
_normalize_foto = field_validator(
    "foto_principal_url", "foto_principal_thumb_url", mode="before"
)(normalize_storage_url)
```

Repetir o mesmo na classe de "leitura resumida" em [app/schemas/pessoa.py:207-209](app/schemas/pessoa.py#L207-L209).

**Step 3: Atualizar endpoint upload pra incluir `thumbnail_url` na resposta**

[app/api/v1/fotos.py:190](app/api/v1/fotos.py#L190):

```python
return FotoUploadResponse(
    id=foto.id,
    arquivo_url=foto.arquivo_url,
    thumbnail_url=foto.thumbnail_url,
    tipo=foto.tipo,
)
```

E em [app/api/v1/fotos.py:457](app/api/v1/fotos.py#L457):

```python
return FotoUploadResponse(
    id=foto.id, arquivo_url=foto.arquivo_url,
    thumbnail_url=foto.thumbnail_url, tipo=foto.tipo,
)
```

**Step 4: Atualizar `buscar_por_rosto` no router**

[app/api/v1/fotos.py:302-316](app/api/v1/fotos.py#L302-L316) — incluir `thumbnail_url` e `foto_principal_thumb_url` no `BuscaRostoItem`.

**Step 5: Rodar testes**

```bash
poetry run pytest tests/ -x -q
poetry run mypy app/schemas/ app/api/v1/fotos.py
```

**Step 6: Commit**

```bash
git add app/schemas/foto.py app/schemas/pessoa.py app/api/v1/fotos.py
git commit -m "feat(api): expõe thumbnail_url nos schemas FotoRead/UploadResponse/BuscaRosto"
```

---

## Fase C — Backfill de fotos existentes

### Task C1: Task arq de backfill

**Files:**
- Create: `app/tasks/thumbnail_backfill.py`
- Modify: `app/worker.py` (registrar task)
- Test: `tests/unit/tasks/test_thumbnail_backfill.py`

**Step 1: Escrever teste**

```python
"""Testes da task de backfill de thumbnails."""

import pytest

from app.tasks.thumbnail_backfill import gerar_thumbnail_backfill_task


@pytest.mark.asyncio
async def test_backfill_pula_foto_com_thumb_existente(ctx_factory, foto_com_thumb):
    """Foto que já tem thumbnail_url não deve ser reprocessada."""
    result = await gerar_thumbnail_backfill_task(ctx_factory(), foto_com_thumb.id)
    assert result["status"] == "já_processada"


@pytest.mark.asyncio
async def test_backfill_pula_midia_nao_imagem(ctx_factory, foto_pdf):
    """PDF não deve gerar thumbnail."""
    result = await gerar_thumbnail_backfill_task(ctx_factory(), foto_pdf.id)
    assert result["status"] == "pulado_nao_imagem"
```

**Step 2: Implementar `app/tasks/thumbnail_backfill.py`**

```python
"""Task arq para backfill de thumbnails em fotos legadas.

Gera ``thumbnail_url`` para fotos cadastradas antes da introdução do
campo. Skip se a foto já tem thumb, é soft-deleted ou não é imagem.
"""

import asyncio
import logging

from sqlalchemy import select

from app.models.foto import Foto
from app.services.storage_service import StorageService
from app.utils.imaging import gerar_thumbnail
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")


async def gerar_thumbnail_backfill_task(ctx: dict, foto_id: int) -> dict:
    """Gera thumbnail de uma foto legada e atualiza thumbnail_url.

    Args:
        ctx: Contexto do worker arq (db_session_factory, storage).
        foto_id: ID da foto a processar.

    Returns:
        Dicionário com status ('sucesso', 'já_processada',
        'pulado_nao_imagem', 'pulado_inexistente', 'erro').
    """
    db_factory = ctx["db_session_factory"]
    storage: StorageService = ctx.get("storage") or StorageService.get()

    async with db_factory() as db:
        try:
            result = await db.execute(
                select(Foto).where(Foto.id == foto_id, Foto.ativo == True)  # noqa: E712
            )
            foto = result.scalar_one_or_none()
            if foto is None:
                return {"status": "pulado_inexistente"}
            if foto.thumbnail_url:
                return {"status": "já_processada"}

            # Inferir content type do arquivo original
            url_lower = foto.arquivo_url.lower()
            if not any(url_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                return {"status": "pulado_nao_imagem"}

            key = extrair_key_da_url(foto.arquivo_url)
            image_bytes = await storage.download(key)

            thumb_bytes = await asyncio.to_thread(gerar_thumbnail, image_bytes)
            filename = key.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "_thumb.jpg"
            thumb_key = storage.generate_key("thumbs", filename)
            thumb_url = await storage.upload(thumb_bytes, thumb_key, content_type="image/jpeg")

            foto.thumbnail_url = thumb_url
            await db.commit()
            logger.info("Thumb backfilled para foto %d", foto_id)
            return {"status": "sucesso"}

        except Exception:
            await db.rollback()
            logger.exception("Erro no backfill da foto %d", foto_id)
            return {"status": "erro"}
```

**Step 3: Registrar no worker**

Em [app/worker.py:100](app/worker.py#L100):

```python
from app.tasks.thumbnail_backfill import gerar_thumbnail_backfill_task

functions = [processar_pdf_task, processar_face_task, gerar_thumbnail_backfill_task]
```

**Step 4: Rodar testes**

```bash
poetry run pytest tests/unit/tasks/test_thumbnail_backfill.py -v
```

**Step 5: Commit**

```bash
git add app/tasks/thumbnail_backfill.py app/worker.py \
        tests/unit/tasks/test_thumbnail_backfill.py
git commit -m "feat(worker): task arq de backfill de thumbnail para fotos legadas"
```

---

### Task C2: Script de enfileiramento do backfill

**Files:**
- Create: `scripts/backfill_thumbnails.py`

**Step 1: Escrever script**

```python
"""Enfileira backfill de thumbnails para todas as fotos sem thumb.

Uso:
    poetry run python scripts/backfill_thumbnails.py            # dry-run
    poetry run python scripts/backfill_thumbnails.py --execute  # enfileira
"""

import argparse
import asyncio

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.foto import Foto


async def main(execute: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Foto.id).where(
                Foto.thumbnail_url.is_(None),
                Foto.ativo == True,  # noqa: E712
            )
        )
        ids = [row[0] for row in result.all()]

    print(f"{len(ids)} fotos sem thumbnail.")
    if not execute:
        print("Dry-run — passe --execute para enfileirar.")
        return

    from arq.connections import create_pool

    from app.worker import WorkerSettings

    pool = await create_pool(WorkerSettings.redis_settings)
    for foto_id in ids:
        await pool.enqueue_job("gerar_thumbnail_backfill_task", foto_id)
    await pool.aclose()
    print(f"{len(ids)} jobs enfileirados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(execute=args.execute))
```

**Step 2: Testar dry-run**

```bash
poetry run python scripts/backfill_thumbnails.py
```

Esperado: imprime `N fotos sem thumbnail.`

**Step 3: Commit**

```bash
git add scripts/backfill_thumbnails.py
git commit -m "chore(scripts): script de backfill de thumbnails para fotos legadas"
```

---

## Fase D — Frontend usa thumbnail_url

### Task D1: Trocar `arquivo_url` por `thumbnail_url` em listagens

**Objetivo:** Em listas/grids, usar thumb. Ao abrir foto em modal/preview, usar `arquivo_url`.

**Files:**
- Modify: `frontend/js/pages/abordagem-detalhe.js`
- Modify: `frontend/js/pages/consulta.js`
- Modify: `frontend/js/pages/ocorrencias.js`

**Step 1: Atualizar `abordagem-detalhe.js`**

[frontend/js/pages/abordagem-detalhe.js:46-49](frontend/js/pages/abordagem-detalhe.js#L46-L49):

```html
<template x-if="p.foto_principal_thumb_url || p.foto_principal_url">
  <img :src="p.foto_principal_thumb_url || p.foto_principal_url"
       style="width:100%;height:100%;object-fit:cover;" loading="lazy">
</template>
```

[frontend/js/pages/abordagem-detalhe.js:216-217](frontend/js/pages/abordagem-detalhe.js#L216-L217) — na grid de fotos da abordagem (não confundir com a foto ampliada):

```html
<div @click="fotoAmpliada = f.arquivo_url">
  <img :src="f.thumbnail_url || f.arquivo_url"
       style="width:100%;height:100%;object-fit:cover;" loading="lazy">
</div>
```

Importante: `fotoAmpliada` continua usando `f.arquivo_url` (foto cheia ao ampliar).

**Step 2: Atualizar `consulta.js`**

Mesma lógica em todas as ocorrências de `<img :src="p.foto_principal_url"`:

```html
<img :src="p.foto_principal_thumb_url || p.foto_principal_url" ...>
```

E em `:src="r.foto_principal_url || r.arquivo_url"`:

```html
<img :src="r.foto_principal_thumb_url || r.foto_principal_url || r.thumbnail_url || r.arquivo_url" ...>
```

Aplicar em todos os pontos listados pelo grep em B4.

**Step 3: Atualizar `ocorrencias.js`**

[frontend/js/pages/ocorrencias.js:115](frontend/js/pages/ocorrencias.js#L115):

```html
<img :src="p.foto_principal_thumb_url || p.foto_principal_url" ...>
```

**Step 4: Teste manual no browser**

```bash
make dev
```

- Abrir uma abordagem com várias fotos (após upload de fotos pós-deploy de B3, OU após rodar backfill).
- DevTools Network: confirmar que as imagens da lista têm `Content-Length` ~25KB, não ~2MB.
- Clicar pra ampliar foto: deve carregar `arquivo_url` cheio.
- Lista de consulta de pessoas: thumbs em vez de fotos cheias.

**Step 5: Commit**

```bash
git add frontend/js/pages/abordagem-detalhe.js frontend/js/pages/consulta.js \
        frontend/js/pages/ocorrencias.js
git commit -m "perf(frontend): listas usam thumbnail_url, modal mantém foto cheia"
```

---

## Verificação final

Antes de mergear:

```bash
# Lint + types
make lint

# Suíte completa
make test

# Migration aplicada e revertível
poetry run alembic downgrade -1
poetry run alembic upgrade head

# Smoke test manual: subir dev, fazer upload de foto, conferir DB:
#   - fotos.thumbnail_url preenchido
#   - pessoas.foto_principal_thumb_url preenchido (se rosto)
#   - thumb visível em /storage/.../thumbs/...
```

**Plano de rollout em produção:**

1. Deploy do código (sem rodar backfill ainda) — uploads novos passam a gerar thumb.
2. Rodar `poetry run python scripts/backfill_thumbnails.py` (dry-run) — ver volume.
3. Rodar `--execute` em janela de menor uso — workers consomem em background.
4. Monitorar logs do worker (`argus`) procurando `Thumb backfilled para foto N`.
5. Sem necessidade de janela de manutenção — frontend já cai gracefully via `thumbnail_url || arquivo_url`.

---

## Notas operacionais

- **Storage extra:** thumbs adicionam ~5% ao bucket (25KB vs 500KB-2MB médios).
- **Auditoria:** intacta — toda foto e toda thumb continua sendo servida via `/storage/{path:path}` autenticado em [main.py:128](app/main.py#L128).
- **Cache:** `Cache-Control: private, max-age=3600` continua válido. ETag novo permite revalidação barata após expirar.
- **Reentrância do upload da thumb:** se o upload da thumb falhar, a foto principal já está salva. `thumbnail_url=NULL` é tratado pelo frontend como fallback para `arquivo_url`. Backfill posterior repara.
- **Não vamos mexer** em embedding facial, OCR, ou outros consumidores internos do byte cheio — esses continuam baixando `arquivo_url` via `storage.download()`.
