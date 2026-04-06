# Relatório de Abordagens — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir a tela `ocorrencia-upload` por uma tela de listagem de abordagens com detalhe completo, upload de RAP PDF e upload de mídias extras.

**Architecture:** Dois novos endpoints REST (`GET /abordagens/` e `GET /abordagens/{id}`) + schema estendido com ocorrências + dois novos arquivos JS de frontend (lista e detalhe). Reutiliza `FotoTipo` para mídias com novo valor `midia_abordagem` e endpoint dedicado para upload de vídeos/docs.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alpine.js, Leaflet (mapa), MinIO/S3.

---

## Task 1: Backend — novo método `list_by_usuario` no repositório

**Files:**
- Modify: `app/repositories/abordagem_repo.py`
- Test: `tests/unit/test_abordagem_service.py`

**Contexto:** O método `list_by_guarnicao` existe mas filtra por `guarnicao_id` — lista as abordagens de toda a guarnição. Para "minhas abordagens" precisamos filtrar por `usuario_id`. Também precisamos de eager loading explícito das pessoas e veículos para o card da lista.

**Step 1: Escrever o teste falhando**

No arquivo `tests/unit/test_abordagem_service.py`, adicionar ao final da classe ou como nova classe:

```python
class TestListarPorUsuario:
    """Testes de listagem de abordagens por usuário."""

    async def test_listar_retorna_apenas_abordagens_do_usuario(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que listar retorna apenas abordagens do usuário logado.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua A, 1",
        )
        await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)

        result = await service.listar_por_usuario(
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(result) == 1
        assert result[0].usuario_id == usuario.id

    async def test_listar_nao_retorna_abordagens_de_outro_usuario(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que abordagens de outro usuário não aparecem na listagem.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        # Cria segundo usuário na mesma guarnição
        outro_usuario = Usuario(
            nome="Outro",
            matricula="9999999",
            senha_hash="x",
            guarnicao_id=guarnicao.id,
        )
        db_session.add(outro_usuario)
        await db_session.flush()

        service = AbordagemService(db_session)
        data = AbordagemCreate(data_hora=datetime.now(UTC))
        await service.criar(data=data, user_id=outro_usuario.id, guarnicao_id=guarnicao.id)

        result = await service.listar_por_usuario(
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(result) == 0
```

**Step 2: Rodar para confirmar falha**

```bash
make test ARGS="tests/unit/test_abordagem_service.py::TestListarPorUsuario -v"
```
Esperado: `AttributeError: 'AbordagemService' object has no attribute 'listar_por_usuario'`

**Step 3: Adicionar `list_by_usuario` no repositório**

Em `app/repositories/abordagem_repo.py`, adicionar método após `list_by_guarnicao`:

```python
async def list_by_usuario(
    self,
    usuario_id: int,
    guarnicao_id: int,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Abordagem]:
    """Lista abordagens de um usuário específico com eager loading.

    Filtra por usuario_id (minhas abordagens) com tenant guard por
    guarnicao_id. Carrega pessoas, veículos e ocorrências via selectin.

    Args:
        usuario_id: ID do oficial autenticado.
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        skip: Registros a pular (paginação).
        limit: Número máximo de resultados.

    Returns:
        Sequência de Abordagens com relacionamentos carregados.
    """
    query = (
        select(Abordagem)
        .options(
            selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
            selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            selectinload(Abordagem.fotos),
            selectinload(Abordagem.ocorrencias),
        )
        .where(
            Abordagem.usuario_id == usuario_id,
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo == True,  # noqa: E712
        )
        .order_by(Abordagem.data_hora.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await self.db.execute(query)
    return result.scalars().unique().all()
```

**Step 4: Adicionar `listar_por_usuario` no service**

Em `app/services/abordagem_service.py`, adicionar método após `listar`:

```python
async def listar_por_usuario(
    self,
    usuario_id: int,
    guarnicao_id: int,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Abordagem]:
    """Lista abordagens do usuário autenticado com paginação.

    Filtra pelo usuário logado (não toda a guarnição), com eager
    loading de pessoas, veículos, fotos e ocorrências.

    Args:
        usuario_id: ID do oficial autenticado.
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        skip: Registros a pular (padrão 0).
        limit: Número máximo de resultados (padrão 20).

    Returns:
        Sequência de Abordagens com relacionamentos carregados.
    """
    return await self.repo.list_by_usuario(usuario_id, guarnicao_id, skip, limit)
```

**Step 5: Rodar testes para confirmar passa**

```bash
make test ARGS="tests/unit/test_abordagem_service.py::TestListarPorUsuario -v"
```
Esperado: PASS nos 2 testes.

**Step 6: Commit**

```bash
git add app/repositories/abordagem_repo.py app/services/abordagem_service.py tests/unit/test_abordagem_service.py
git commit -m "feat(abordagens): adicionar listagem por usuario com eager loading"
```

---

## Task 2: Backend — extender `AbordagemDetail` e adicionar `FotoTipo.midia_abordagem`

**Files:**
- Modify: `app/schemas/abordagem.py`
- Modify: `app/schemas/foto.py`

**Contexto:** `AbordagemDetail` existe mas não inclui `ocorrencias`. `FotoTipo` não tem o valor `midia_abordagem`. Ambos são pré-requisitos para os endpoints e frontend.

**Step 1: Adicionar `midia_abordagem` ao `FotoTipo`**

Em `app/schemas/foto.py`, no `FotoTipo` StrEnum, adicionar após `documento`:

```python
midia_abordagem = "midia_abordagem"
```

O enum completo ficará:
```python
class FotoTipo(StrEnum):
    rosto = "rosto"
    corpo = "corpo"
    placa = "placa"
    veiculo = "veiculo"
    documento = "documento"
    midia_abordagem = "midia_abordagem"
```

**Step 2: Extender `AbordagemDetail` com ocorrências**

Em `app/schemas/abordagem.py`, adicionar import no topo:

```python
from app.schemas.ocorrencia import OcorrenciaRead
```

Alterar a classe `AbordagemDetail`:

```python
class AbordagemDetail(AbordagemRead):
    """Dados detalhados de uma abordagem com todos os relacionamentos.

    Estende AbordagemRead com pessoas, veículos, fotos e ocorrências vinculadas.

    Attributes:
        pessoas: Lista de pessoas abordadas.
        veiculos: Lista de veículos envolvidos com pessoa associada.
        fotos: Lista de fotos registradas (inclui mídias).
        ocorrencias: Lista de ocorrências (RAPs) vinculadas.
    """

    pessoas: list[PessoaRead] = []
    veiculos: list[VeiculoAbordagemRead] = []
    fotos: list[FotoRead] = []
    ocorrencias: list[OcorrenciaRead] = []
```

**Step 3: Adicionar validador para serializar `AbordagemDetail` com pessoas das associações**

O modelo retorna `AbordagemPessoa` (não `Pessoa` diretamente). Precisamos de um schema intermediário. Adicionar antes de `AbordagemDetail`:

```python
class PessoaAbordagemRead(BaseModel):
    """Pessoa abordada com dados resumidos para exibição em card/detalhe.

    Attributes:
        id: Identificador único da pessoa.
        nome: Nome completo.
        foto_principal_url: URL da foto de perfil (opcional).
        apelido: Apelido ou nome de rua (opcional).
    """

    id: int
    nome: str
    foto_principal_url: str | None = None
    apelido: str | None = None

    model_config = {"from_attributes": True}
```

E alterar `AbordagemDetail.pessoas` para usar este schema:

```python
pessoas: list[PessoaAbordagemRead] = []
```

**Step 4: Verificar lint**

```bash
make lint
```
Esperado: sem erros.

**Step 5: Commit**

```bash
git add app/schemas/abordagem.py app/schemas/foto.py
git commit -m "feat(schemas): extender AbordagemDetail com ocorrencias e adicionar FotoTipo.midia_abordagem"
```

---

## Task 3: Backend — endpoints `GET /abordagens/` e `GET /abordagens/{id}`

**Files:**
- Modify: `app/api/v1/abordagens.py`
- Test: `tests/integration/` (criar novo arquivo)

**Contexto:** O router só tem `POST /abordagens/`. Precisamos dos dois GETs. O `AbordagemDetail` precisa ser serializado corretamente a partir dos relacionamentos lazy-loaded.

**Step 1: Escrever testes de integração**

Criar `tests/integration/test_abordagens_api.py`:

```python
"""Testes de integração dos endpoints de listagem de abordagens."""

import pytest
from httpx import AsyncClient

from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


class TestListarAbordagens:
    """Testes do endpoint GET /abordagens/."""

    async def test_listar_retorna_minhas_abordagens(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Testa que o endpoint retorna as abordagens do usuário autenticado.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
            abordagem: Fixture de abordagem criada.
        """
        response = await client.get("/api/v1/abordagens/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == abordagem.id

    async def test_listar_requer_autenticacao(self, client: AsyncClient):
        """Testa que o endpoint requer token JWT.

        Args:
            client: Cliente HTTP de teste.
        """
        response = await client.get("/api/v1/abordagens/")
        assert response.status_code == 401

    async def test_detalhe_retorna_abordagem_completa(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Testa que o detalhe retorna dados completos com relacionamentos.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
            abordagem: Fixture de abordagem criada.
        """
        response = await client.get(
            f"/api/v1/abordagens/{abordagem.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == abordagem.id
        assert "pessoas" in data
        assert "veiculos" in data
        assert "fotos" in data
        assert "ocorrencias" in data

    async def test_detalhe_404_abordagem_inexistente(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que detalhe de abordagem inexistente retorna 404.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
        """
        response = await client.get("/api/v1/abordagens/99999", headers=auth_headers)
        assert response.status_code == 404
```

**Step 2: Rodar para confirmar falha**

```bash
make test ARGS="tests/integration/test_abordagens_api.py -v"
```
Esperado: 404 nos endpoints (ainda não existem).

**Step 3: Implementar os endpoints**

Em `app/api/v1/abordagens.py`, adicionar imports no topo:

```python
from fastapi import APIRouter, Depends, Query, Request, status
```

(substituindo o import atual de `APIRouter, Depends, Request, status`)

E adicionar `AbordagemDetail` no import de schemas:

```python
from app.schemas.abordagem import (
    AbordagemCreate,
    AbordagemDetail,
    AbordagemRead,
)
```

E adicionar `get_current_user` nos imports de dependências:

```python
from app.dependencies import get_current_user, get_current_user_with_guarnicao
```

Adicionar os dois endpoints após o `criar_abordagem`:

```python
@router.get("/", response_model=list[AbordagemDetail])
@limiter.limit("30/minute")
async def listar_abordagens(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemDetail]:
    """Lista abordagens do usuário autenticado com paginação.

    Retorna apenas as abordagens realizadas pelo próprio usuário,
    com pessoas, veículos, fotos e ocorrências carregados.

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular (padrão 0).
        limit: Máximo de resultados 1-100 (padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemDetail ordenada por data/hora decrescente.

    Status Code:
        200: Lista retornada.
        429: Rate limit (30/min).
    """
    service = AbordagemService(db)
    abordagens = await service.listar_por_usuario(
        usuario_id=user.id,
        guarnicao_id=user.guarnicao_id,
        skip=skip,
        limit=limit,
    )
    return [_serializar_detalhe(a) for a in abordagens]


@router.get("/{abordagem_id}", response_model=AbordagemDetail)
@limiter.limit("60/minute")
async def detalhe_abordagem(
    request: Request,
    abordagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AbordagemDetail:
    """Retorna detalhe completo de uma abordagem.

    Carrega todos os relacionamentos: pessoas abordadas, veículos,
    fotos (inclui mídias) e ocorrências (RAPs) vinculadas.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: Identificador da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        AbordagemDetail com todos os relacionamentos.

    Raises:
        HTTPException 404: Abordagem não encontrada ou não pertence à guarnição.

    Status Code:
        200: Detalhe retornado.
        404: Abordagem não encontrada.
        429: Rate limit (60/min).
    """
    service = AbordagemService(db)
    abordagem = await service.buscar_detalhe(abordagem_id, user.guarnicao_id)
    return _serializar_detalhe(abordagem)


def _serializar_detalhe(abordagem) -> AbordagemDetail:
    """Serializa Abordagem com relacionamentos para AbordagemDetail.

    Extrai Pessoa dos objetos AbordagemPessoa e Veiculo dos
    AbordagemVeiculo antes de chamar model_validate.

    Args:
        abordagem: Objeto Abordagem com relacionamentos carregados.

    Returns:
        AbordagemDetail serializado.
    """
    from app.schemas.abordagem import PessoaAbordagemRead, VeiculoAbordagemRead
    from app.schemas.foto import FotoRead
    from app.schemas.ocorrencia import OcorrenciaRead

    pessoas = [
        PessoaAbordagemRead.model_validate(ap.pessoa)
        for ap in abordagem.pessoas
        if ap.ativo and ap.pessoa
    ]
    veiculos = []
    for av in abordagem.veiculos:
        if av.ativo and av.veiculo:
            v = VeiculoAbordagemRead.model_validate(av.veiculo)
            v.pessoa_id = av.pessoa_id
            veiculos.append(v)
    fotos = [FotoRead.model_validate(f) for f in abordagem.fotos if f.ativo]
    ocorrencias = [OcorrenciaRead.model_validate(o) for o in abordagem.ocorrencias if o.ativo]

    detail = AbordagemDetail.model_validate(abordagem)
    detail.pessoas = pessoas
    detail.veiculos = veiculos
    detail.fotos = fotos
    detail.ocorrencias = ocorrencias
    return detail
```

**Nota:** `AbordagemDetail` precisa ter `model_config = {"from_attributes": True}` — já está em `AbordagemRead` que ela herda.

**Step 4: Rodar testes**

```bash
make test ARGS="tests/integration/test_abordagens_api.py -v"
```
Esperado: todos PASS.

**Step 5: Verificar lint**

```bash
make lint
```

**Step 6: Commit**

```bash
git add app/api/v1/abordagens.py tests/integration/test_abordagens_api.py
git commit -m "feat(api): adicionar GET /abordagens/ e GET /abordagens/{id}"
```

---

## Task 4: Backend — endpoint `POST /midias/upload` para vídeos e documentos

**Files:**
- Modify: `app/api/v1/fotos.py`

**Contexto:** O endpoint `/fotos/upload` valida magic bytes de imagem e rejeita vídeos. Para mídias da abordagem (vídeos, autorizações de entrada), precisamos de um endpoint separado que aceite qualquer arquivo binário até 200MB.

**Step 1: Adicionar o endpoint ao final de `app/api/v1/fotos.py`**

Adicionar constantes no topo do arquivo, após `MAX_IMAGE_SIZE`:

```python
#: Tamanho máximo de upload de mídia (200 MB — para vídeos).
MAX_MIDIA_SIZE = 200 * 1024 * 1024
#: MIME types permitidos para upload de mídia.
ALLOWED_MIDIA_MIMES = {
    "image/jpeg", "image/png", "image/webp",
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm",
    "application/pdf",
}
```

Adicionar endpoint ao final do router:

```python
@router.post(
    "/midias",
    response_model=FotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def upload_midia_abordagem(
    request: Request,
    file: UploadFile,
    abordagem_id: int = Form(..., gt=0),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> FotoUploadResponse:
    """Faz upload de mídia (foto, vídeo ou PDF) vinculada a uma abordagem.

    Aceita imagens, vídeos (MP4, MOV, AVI, WebM) e PDFs até 200MB.
    Usado para registrar autorizações de entrada em residência,
    vídeos de ocorrência e outros documentos operacionais.

    Args:
        request: Objeto Request do FastAPI.
        file: Arquivo de mídia (multipart/form-data).
        abordagem_id: ID da abordagem a vincular (obrigatório).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        FotoUploadResponse com id, url e tipo="midia_abordagem".

    Raises:
        HTTPException 400: Formato não permitido.
        HTTPException 413: Arquivo excede 200 MB.

    Status Code:
        201: Mídia enviada.
        429: Rate limit (20/min).
    """
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIDIA_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato não permitido: {content_type}. "
                   "Aceitos: imagens, vídeos MP4/MOV/AVI/WebM e PDF.",
        )

    file_bytes = await ler_upload_com_limite(file, MAX_MIDIA_SIZE)
    filename = file.filename or "midia"

    service = FotoService(db)
    try:
        foto = await service.upload_foto(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            abordagem_id=abordagem_id,
            tipo=FotoTipo.midia_abordagem,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao fazer upload. Verifique o storage e tente novamente.",
        ) from exc

    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="midia_abordagem",
        recurso_id=foto.id,
        detalhes={"abordagem_id": abordagem_id, "content_type": content_type},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return FotoUploadResponse(id=foto.id, arquivo_url=foto.arquivo_url, tipo=foto.tipo)
```

**Step 2: Verificar lint**

```bash
make lint
```

**Step 3: Commit**

```bash
git add app/api/v1/fotos.py
git commit -m "feat(fotos): adicionar endpoint POST /midias para upload de videos e documentos"
```

---

## Task 5: Frontend — página de lista `ocorrencias.js`

**Files:**
- Create: `frontend/js/pages/ocorrencias.js`

**Contexto:** Substitui `ocorrencia-upload.js`. Exibe cards de abordagens com avatares, data, endereço, badges RAP e mídias. Clicar navega para `abordagem-detalhe`.

**Step 1: Criar o arquivo**

```javascript
/**
 * Página de listagem de abordagens (Relatório de Abordagens) — Argus AI.
 *
 * Lista as abordagens realizadas pelo usuário logado, com filtro local
 * por nome ou placa, badge de RAP vinculada e navegação para detalhe.
 */

function renderOcorrencias() {
  return `
    <div x-data="ocorrenciasPage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.1em;margin:0;">
          RELATÓRIO DE ABORDAGENS
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;margin-top:4px;"
           x-text="loading ? 'CARREGANDO...' : total + ' REGISTROS'">
        </p>
      </div>

      <!-- Busca local -->
      <div style="display:flex;align-items:center;gap:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 12px;">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="search" x-model="filtro" placeholder="Buscar por nome, placa, endereço..."
          style="background:none;border:none;outline:none;color:var(--color-text);font-family:var(--font-data);font-size:13px;width:100%;">
      </div>

      <!-- Loading -->
      <div x-show="loading" style="text-align:center;padding:32px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-danger);" x-text="erro"></p>
        <button @click="carregar()" class="btn btn-secondary" style="margin-top:8px;width:auto;padding:6px 16px;">Tentar novamente</button>
      </div>

      <!-- Lista -->
      <template x-for="ab in abordagensFiltradas" :key="ab.id">
        <div class="glass-card" :class="ab.ocorrencias?.length ? 'card-led-blue' : ''"
             style="padding:12px;cursor:pointer;border-radius:4px;"
             @click="abrirDetalhe(ab.id)">

          <!-- Row principal -->
          <div style="display:flex;align-items:center;gap:10px;">
            <!-- Avatares -->
            <div style="display:flex;">
              <template x-for="(p, i) in ab.pessoas.slice(0, 3)" :key="p.id">
                <div :style="'width:36px;height:36px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:11px;font-weight:700;color:var(--color-primary);flex-shrink:0;' + (i > 0 ? 'margin-left:-8px;' : '') + (p.foto_principal_url ? 'padding:0;overflow:hidden;' : '')">
                  <template x-if="p.foto_principal_url">
                    <img :src="p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                  </template>
                  <template x-if="!p.foto_principal_url">
                    <span x-text="iniciais(p.nome)"></span>
                  </template>
                </div>
              </template>
              <template x-if="ab.pessoas.length === 0">
                <div style="width:36px;height:36px;border-radius:4px;border:1px dashed var(--color-border);display:flex;align-items:center;justify-content:center;">
                  <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
              </template>
            </div>

            <!-- Info -->
            <div style="flex:1;min-width:0;">
              <div style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
                   x-text="formatarDataHora(ab.data_hora)"></div>
              <div style="font-family:var(--font-data);font-size:13px;font-weight:600;color:var(--color-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="nomesPessoas(ab.pessoas) || 'Sem abordados registrados'"></div>
              <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="ab.endereco_texto || 'Endereço não disponível'"></div>
            </div>
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;"><path d="M9 18l6-6-6-6"/></svg>
          </div>

          <!-- Footer badges -->
          <div style="display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap;">
            <template x-if="ab.ocorrencias?.length > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);">RAP vinculada</span>
            </template>
            <template x-if="!ab.ocorrencias?.length">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(255,107,0,0.1);color:var(--color-danger);border:1px solid rgba(255,107,0,0.25);">Sem RAP</span>
            </template>
            <template x-if="midias(ab.fotos) > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,212,255,0.08);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);"
                    x-text="midias(ab.fotos) + ' mídia' + (midias(ab.fotos) > 1 ? 's' : '')"></span>
            </template>
            <template x-if="ab.veiculos?.length > 0">
              <span style="margin-left:auto;font-family:var(--font-display);font-size:9px;color:var(--color-text-dim);background:var(--color-surface);border:1px solid var(--color-border);border-radius:2px;padding:1px 5px;"
                    x-text="ab.veiculos.length + ' veículo' + (ab.veiculos.length > 1 ? 's' : '')"></span>
            </template>
          </div>
        </div>
      </template>

      <!-- Vazio -->
      <div x-show="!loading && !erro && abordagensFiltradas.length === 0" style="text-align:center;padding:32px 0;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-text-muted);">
          <span x-show="filtro">Nenhum resultado para "<span x-text="filtro"></span>"</span>
          <span x-show="!filtro">Nenhuma abordagem registrada ainda.</span>
        </p>
      </div>

      <!-- Carregar mais -->
      <div x-show="!loading && temMais" style="text-align:center;">
        <button @click="carregarMais()" :disabled="carregandoMais" class="btn btn-secondary"
                style="width:auto;padding:8px 24px;font-size:12px;">
          <span x-show="!carregandoMais">Carregar mais</span>
          <span x-show="carregandoMais">Carregando...</span>
        </button>
      </div>

    </div>
  `;
}

function ocorrenciasPage() {
  return {
    abordagens: [],
    filtro: '',
    loading: true,
    carregandoMais: false,
    erro: null,
    skip: 0,
    limit: 20,
    total: 0,
    temMais: false,

    get abordagensFiltradas() {
      if (!this.filtro.trim()) return this.abordagens;
      const q = this.filtro.toLowerCase();
      return this.abordagens.filter(ab => {
        const nomes = ab.pessoas.map(p => p.nome.toLowerCase()).join(' ');
        const placas = ab.veiculos.map(v => v.placa.toLowerCase()).join(' ');
        const end = (ab.endereco_texto || '').toLowerCase();
        return nomes.includes(q) || placas.includes(q) || end.includes(q);
      });
    },

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.loading = true;
      this.erro = null;
      this.skip = 0;
      try {
        const data = await api.get(`/abordagens/?skip=0&limit=${this.limit}`);
        this.abordagens = data;
        this.total = data.length;
        this.temMais = data.length === this.limit;
      } catch (e) {
        this.erro = 'Erro ao carregar abordagens. Tente novamente.';
      } finally {
        this.loading = false;
      }
    },

    async carregarMais() {
      this.carregandoMais = true;
      this.skip += this.limit;
      try {
        const data = await api.get(`/abordagens/?skip=${this.skip}&limit=${this.limit}`);
        this.abordagens = [...this.abordagens, ...data];
        this.total = this.abordagens.length;
        this.temMais = data.length === this.limit;
      } catch (e) {
        this.skip -= this.limit;
      } finally {
        this.carregandoMais = false;
      }
    },

    abrirDetalhe(id) {
      const appEl = document.querySelector('[x-data]');
      if (appEl && appEl._x_dataStack) {
        appEl._x_dataStack[0]._abordagemId = id;
        appEl._x_dataStack[0].navigate('abordagem-detalhe');
      }
    },

    iniciais(nome) {
      return nome.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },

    nomesPessoas(pessoas) {
      if (!pessoas.length) return '';
      const nomes = pessoas.slice(0, 2).map(p => p.nome.split(' ')[0].toUpperCase());
      const extra = pessoas.length > 2 ? ` +${pessoas.length - 2}` : '';
      return nomes.join(' · ') + extra;
    },

    midias(fotos) {
      return (fotos || []).filter(f => f.tipo === 'midia_abordagem').length;
    },

    formatarDataHora(dt) {
      const d = new Date(dt);
      return d.toLocaleDateString('pt-BR') + ' · ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    },
  };
}
```

**Step 2: Commit**

```bash
git add frontend/js/pages/ocorrencias.js
git commit -m "feat(frontend): adicionar pagina de listagem de abordagens (ocorrencias.js)"
```

---

## Task 6: Frontend — página de detalhe `abordagem-detalhe.js`

**Files:**
- Create: `frontend/js/pages/abordagem-detalhe.js`

**Contexto:** Exibe detalhe completo de uma abordagem. Usa o mesmo padrão de mapa Leaflet que `pessoa-detalhe.js`. Upload de RAP via `POST /ocorrencias/`. Upload de mídias via `POST /fotos/midias`.

**Step 1: Criar o arquivo**

```javascript
/**
 * Página de detalhe de abordagem — Argus AI.
 *
 * Exibe dados completos de uma abordagem: pessoas abordadas (clicáveis),
 * veículos, mapa Leaflet, observação, upload de RAP PDF e upload de mídias.
 */

function renderAbordagemDetalhe() {
  return `
    <div x-data="abordagemDetalhePage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Loading inicial -->
      <div x-show="loading" style="text-align:center;padding:48px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="color:var(--color-danger);font-family:var(--font-data);font-size:13px;" x-text="erro"></p>
      </div>

      <!-- Conteúdo principal -->
      <template x-if="!loading && !erro && ab">

        <div style="display:flex;flex-direction:column;gap:12px;">

          <!-- ID + Data/Hora + badge RAP -->
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span style="font-family:var(--font-display);font-size:10px;color:var(--color-text-dim);" x-text="'#' + ab.id"></span>
            <span style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);" x-text="formatarDataHora(ab.data_hora)"></span>
            <span x-show="ab.ocorrencias?.length > 0"
                  style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);text-transform:uppercase;letter-spacing:0.08em;">RAP</span>
          </div>

          <!-- ABORDADOS -->
          <div class="glass-card card-led-blue" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Abordados</span>
              <div x-show="ab.pessoas.length === 0" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">Nenhum abordado registrado.</div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;">
                <template x-for="p in ab.pessoas" :key="p.id">
                  <div style="display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;" @click="abrirFicha(p.id)">
                    <div style="width:54px;height:54px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;overflow:hidden;transition:border-color 0.15s;"
                         onmouseover="this.style.borderColor='var(--color-primary)'" onmouseout="this.style.borderColor='rgba(0,212,255,0.2)'">
                      <template x-if="p.foto_principal_url">
                        <img :src="p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                      </template>
                      <template x-if="!p.foto_principal_url">
                        <span style="font-family:var(--font-display);font-size:16px;font-weight:700;color:var(--color-primary);" x-text="iniciais(p.nome)"></span>
                      </template>
                    </div>
                    <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-muted);text-align:center;max-width:56px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                          x-text="p.nome.split(' ')[0]"></span>
                  </div>
                </template>
              </div>
              <p x-show="ab.pessoas.length > 0" style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;">Toque para abrir a ficha</p>
            </div>
          </div>

          <!-- VEÍCULOS -->
          <div x-show="ab.veiculos.length > 0" class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Veículos</span>
              <template x-for="v in ab.veiculos" :key="v.id">
                <div style="display:flex;align-items:center;gap:10px;padding:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;">
                  <div style="width:52px;height:36px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:3px;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">
                    <template x-if="fotoVeiculo(v.id)">
                      <img :src="fotoVeiculo(v.id)" style="width:100%;height:100%;object-fit:cover;">
                    </template>
                    <template x-if="!fotoVeiculo(v.id)">
                      <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><rect x="2" y="7" width="20" height="13" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>
                    </template>
                  </div>
                  <div>
                    <div style="font-family:var(--font-display);font-size:12px;font-weight:700;color:var(--color-primary);letter-spacing:0.1em;" x-text="v.placa"></div>
                    <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);"
                         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- LOCALIZAÇÃO -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Localização</span>
              <div x-show="ab.latitude && ab.longitude">
                <div :id="'mapa-ab-' + ab.id" style="width:100%;height:120px;border-radius:4px;border:1px solid var(--color-border);"></div>
              </div>
              <div x-show="!ab.latitude || !ab.longitude" style="height:60px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;display:flex;align-items:center;justify-content:center;">
                <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Coordenadas não disponíveis</span>
              </div>
              <div x-show="ab.endereco_texto" style="display:flex;align-items:center;gap:6px;">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);flex-shrink:0;"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                <span style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);" x-text="ab.endereco_texto"></span>
              </div>
            </div>
          </div>

          <!-- OBSERVAÇÃO -->
          <div x-show="ab.observacao" class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Observação</span>
              <div style="background:var(--color-surface);border:1px solid var(--color-border);border-left:2px solid rgba(0,212,255,0.3);border-radius:4px;padding:10px 12px;font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);line-height:1.5;"
                   x-text="ab.observacao"></div>
            </div>
          </div>

          <hr style="border:none;border-top:1px solid var(--color-border);margin:4px 0;">

          <!-- RAP -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Boletim de Ocorrência (RAP)</span>
                <span x-show="ab.ocorrencias?.length > 0"
                      style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);text-transform:uppercase;">Vinculada</span>
              </div>

              <!-- RAP já vinculada -->
              <template x-if="ab.ocorrencias?.length > 0">
                <template x-for="oc in ab.ocorrencias" :key="oc.id">
                  <div style="display:flex;align-items:center;gap:10px;border:1px solid rgba(0,255,136,0.3);background:rgba(0,255,136,0.04);border-radius:4px;padding:10px;">
                    <div style="width:32px;height:32px;border-radius:4px;background:rgba(0,255,136,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-success);"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div style="flex:1;min-width:0;">
                      <div style="font-family:var(--font-display);font-size:11px;color:var(--color-success);" x-text="oc.numero_ocorrencia"></div>
                      <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);"
                           x-text="'Data: ' + new Date(oc.data_ocorrencia).toLocaleDateString('pt-BR')"></div>
                    </div>
                    <a :href="oc.arquivo_pdf_url" target="_blank"
                       style="color:var(--color-text-dim);display:flex;align-items:center;"
                       title="Abrir PDF">
                      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    </a>
                  </div>
                </template>
              </template>

              <!-- Formulário de upload RAP -->
              <template x-if="!ab.ocorrencias?.length">
                <div style="display:flex;flex-direction:column;gap:8px;">
                  <!-- Arquivo -->
                  <div style="border:1px dashed rgba(0,212,255,0.25);border-radius:4px;padding:12px;display:flex;align-items:center;gap:10px;cursor:pointer;background:rgba(0,212,255,0.03);"
                       :style="rapFile ? 'border-color:rgba(0,255,136,0.3);background:rgba(0,255,136,0.04);' : ''"
                       @click="$refs.rapInput.click()">
                    <div style="width:32px;height:32px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <div>
                      <div style="font-family:var(--font-display);font-size:11px;color:var(--color-primary);"
                           x-text="rapFile ? rapFile.name : 'Selecionar PDF da RAP'"></div>
                      <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);"
                           x-text="rapFile ? formatarTamanho(rapFile.size) : 'Toque para selecionar o arquivo'"></div>
                    </div>
                    <input type="file" accept="application/pdf" x-ref="rapInput" style="display:none;" @change="rapFile = $event.target.files[0]">
                  </div>
                  <!-- Número -->
                  <div>
                    <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Número da RAP</div>
                    <input type="text" x-model="rapNumero" placeholder="Ex: RAP 2026/004820"
                      style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 10px;color:var(--color-text);font-family:var(--font-data);font-size:13px;outline:none;">
                  </div>
                  <!-- Data -->
                  <div>
                    <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Data da Ocorrência</div>
                    <input type="text" x-model="rapData" placeholder="DD/MM/AAAA" maxlength="10"
                      @input="rapData = formatarData($event.target.value)"
                      style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 10px;color:var(--color-text);font-family:var(--font-data);font-size:13px;outline:none;">
                  </div>
                  <!-- Erro RAP -->
                  <p x-show="rapErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="rapErro"></p>
                  <!-- Botão enviar -->
                  <button @click="enviarRap()" :disabled="!rapFile || !rapNumero || !rapData || enviandoRap"
                          style="width:100%;padding:10px;background:var(--color-primary);color:var(--color-bg);font-family:var(--font-display);font-size:12px;font-weight:700;border:none;border-radius:4px;cursor:pointer;letter-spacing:0.08em;opacity:1;"
                          :style="(!rapFile || !rapNumero || !rapData || enviandoRap) ? 'opacity:0.4;cursor:not-allowed;' : ''">
                    <span x-show="!enviandoRap">ENVIAR OCORRÊNCIA</span>
                    <span x-show="enviandoRap">ENVIANDO...</span>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- MÍDIAS -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Mídias</span>
                <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);">fotos · vídeos · autorizações</span>
              </div>

              <!-- Grid de mídias existentes + botão add -->
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <template x-for="f in midiasAbordagem" :key="f.id">
                  <div style="width:64px;height:64px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:4px;overflow:hidden;cursor:pointer;position:relative;"
                       @click="fotoAmpliada = f.arquivo_url">
                    <template x-if="f.arquivo_url.match(/\\.(mp4|mov|avi|webm)/i)">
                      <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;">
                        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/></svg>
                        <span style="font-family:var(--font-display);font-size:7px;color:var(--color-primary);">VID</span>
                      </div>
                    </template>
                    <template x-if="!f.arquivo_url.match(/\\.(mp4|mov|avi|webm)/i)">
                      <img :src="f.arquivo_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                    </template>
                  </div>
                </template>

                <!-- Botão adicionar -->
                <div style="width:64px;height:64px;border:1px dashed rgba(0,212,255,0.25);border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;cursor:pointer;background:rgba(0,212,255,0.03);"
                     :style="enviandoMidia ? 'opacity:0.5;cursor:not-allowed;' : ''"
                     @click="!enviandoMidia && $refs.midiaInput.click()">
                  <template x-if="!enviandoMidia">
                    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </template>
                  <template x-if="enviandoMidia">
                    <div style="width:16px;height:16px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;"></div>
                  </template>
                  <span style="font-family:var(--font-display);font-size:8px;color:var(--color-text-dim);" x-text="enviandoMidia ? '' : 'ADD'"></span>
                  <input type="file" accept="image/*,video/*,application/pdf" x-ref="midiaInput" style="display:none;"
                         @change="enviarMidia($event.target.files[0])">
                </div>
              </div>

              <!-- Erro mídia -->
              <p x-show="midiaErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="midiaErro"></p>
            </div>
          </div>

        </div>
      </template>

      <!-- Modal foto ampliada -->
      <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
           style="position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
        <img :src="fotoAmpliada" style="max-width:100%;max-height:80vh;border-radius:4px;" @click.stop>
      </div>

    </div>
  `;
}

function abordagemDetalhePage() {
  return {
    ab: null,
    loading: true,
    erro: null,
    fotoAmpliada: null,
    // RAP
    rapFile: null,
    rapNumero: '',
    rapData: '',
    rapErro: null,
    enviandoRap: false,
    // Mídias
    enviandoMidia: false,
    midiaErro: null,
    // Mapa
    _mapa: null,
    _mapaObserver: null,

    get midiasAbordagem() {
      return (this.ab?.fotos || []).filter(f => f.tipo === 'midia_abordagem');
    },

    async init() {
      const appEl = document.querySelector('[x-data]');
      const abordagemId = appEl?._x_dataStack?.[0]?._abordagemId;
      if (!abordagemId) {
        this.erro = 'ID da abordagem não encontrado.';
        this.loading = false;
        return;
      }
      try {
        this.ab = await api.get(`/abordagens/${abordagemId}`);
      } catch (e) {
        this.erro = 'Erro ao carregar abordagem.';
      } finally {
        this.loading = false;
      }
      if (this.ab?.latitude && this.ab?.longitude) {
        this.$nextTick(() => this._initMapa());
      }
    },

    _initMapa() {
      if (this._mapaObserver) this._mapaObserver.disconnect();
      const divId = `mapa-ab-${this.ab.id}`;
      const tryInit = () => {
        const div = document.getElementById(divId);
        if (!div) return false;
        if (this._mapa) { this._mapa.remove(); this._mapa = null; }
        this._mapa = L.map(div, { zoomControl: false, dragging: false, scrollWheelZoom: false })
          .setView([this.ab.latitude, this.ab.longitude], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap'
        }).addTo(this._mapa);
        L.circleMarker([this.ab.latitude, this.ab.longitude], {
          radius: 8, color: '#00D4FF', fillColor: '#00D4FF', fillOpacity: 0.8, weight: 2
        }).addTo(this._mapa);
        return true;
      };
      if (!tryInit()) {
        this._mapaObserver = new MutationObserver(() => { if (tryInit()) this._mapaObserver.disconnect(); });
        this._mapaObserver.observe(document.body, { childList: true, subtree: true });
      }
    },

    fotoVeiculo(veiculoId) {
      const f = (this.ab?.fotos || []).find(f => f.veiculo_id === veiculoId && f.tipo === 'veiculo');
      return f?.arquivo_url || null;
    },

    abrirFicha(pessoaId) {
      const appEl = document.querySelector('[x-data]');
      if (appEl && appEl._x_dataStack) {
        appEl._x_dataStack[0]._pessoaId = pessoaId;
        appEl._x_dataStack[0].navigate('pessoa-detalhe');
      }
    },

    async enviarRap() {
      this.rapErro = null;
      const partes = this.rapData.split('/');
      if (partes.length !== 3) { this.rapErro = 'Data inválida. Use DD/MM/AAAA.'; return; }
      const dataIso = `${partes[2]}-${partes[1].padStart(2,'0')}-${partes[0].padStart(2,'0')}`;
      this.enviandoRap = true;
      try {
        const form = new FormData();
        form.append('arquivo_pdf', this.rapFile);
        form.append('numero_ocorrencia', this.rapNumero);
        form.append('abordagem_id', String(this.ab.id));
        form.append('data_ocorrencia', dataIso);
        const result = await api.uploadFile('/ocorrencias/', this.rapFile, {
          numero_ocorrencia: this.rapNumero,
          abordagem_id: this.ab.id,
          data_ocorrencia: dataIso,
        });
        this.ab.ocorrencias = [...(this.ab.ocorrencias || []), result];
        this.rapFile = null;
        this.rapNumero = '';
        this.rapData = '';
      } catch (e) {
        this.rapErro = 'Erro ao enviar RAP. Verifique o arquivo e tente novamente.';
      } finally {
        this.enviandoRap = false;
      }
    },

    async enviarMidia(file) {
      if (!file) return;
      this.midiaErro = null;
      this.enviandoMidia = true;
      try {
        const result = await api.uploadFile('/fotos/midias', file, {
          abordagem_id: this.ab.id,
        });
        this.ab.fotos = [...(this.ab.fotos || []), result];
      } catch (e) {
        this.midiaErro = 'Erro ao enviar mídia. Tente novamente.';
      } finally {
        this.enviandoMidia = false;
      }
    },

    iniciais(nome) {
      return nome.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },

    formatarDataHora(dt) {
      const d = new Date(dt);
      return d.toLocaleDateString('pt-BR') + ' · ' + d.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
    },

    formatarTamanho(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    formatarData(v) {
      const nums = v.replace(/\D/g, '');
      if (nums.length <= 2) return nums;
      if (nums.length <= 4) return nums.slice(0, 2) + '/' + nums.slice(2);
      return nums.slice(0, 2) + '/' + nums.slice(2, 4) + '/' + nums.slice(4, 8);
    },
  };
}
```

**Step 2: Commit**

```bash
git add frontend/js/pages/abordagem-detalhe.js
git commit -m "feat(frontend): adicionar pagina de detalhe de abordagem"
```

---

## Task 7: Frontend — atualizar `index.html` e `app.js`

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`

**Contexto:** Registrar os dois novos scripts, atualizar o mapa de renderers, trocar o label da tab de "Ocorrência" para "Relatórios" e remover `ocorrencia-upload.js`.

**Step 1: Atualizar `index.html`**

Localizar e substituir:

```html
<script src="/js/pages/ocorrencia-upload.js?v=3"></script>
```

Por:

```html
<script src="/js/pages/ocorrencias.js?v=1"></script>
<script src="/js/pages/abordagem-detalhe.js?v=1"></script>
```

Localizar e substituir o botão da tab Ocorrência:

```html
      <button type="button" aria-label="Navegar para Ocorrência" class="bottom-nav-btn" :class="{ active: currentPage === 'ocorrencia-upload' }" @click="navigate('ocorrencia-upload')">
```

Por:

```html
      <button type="button" aria-label="Navegar para Relatório de Abordagens" class="bottom-nav-btn" :class="{ active: currentPage === 'ocorrencias' || currentPage === 'abordagem-detalhe' }" @click="navigate('ocorrencias')">
```

E o label interno da tab (linha seguinte ao SVG):

```html
          <span class="bottom-nav-label">Ocorrência</span>
```

Por:

```html
          <span class="bottom-nav-label">Relatórios</span>
```

**Step 2: Atualizar `app.js` — registrar renderers**

Em `frontend/js/app.js`, no objeto `renderers` dentro de `_renderInto`, substituir:

```javascript
        "ocorrencia-upload": renderOcorrenciaUpload,
```

Por:

```javascript
        "ocorrencias": renderOcorrencias,
        "abordagem-detalhe": renderAbordagemDetalhe,
```

**Step 3: Verificar que o app carrega sem erros**

Abrir o browser em `http://localhost:8000`, fazer login e clicar na tab "Relatórios". Esperado: lista de abordagens carrega.

**Step 4: Commit**

```bash
git add frontend/index.html frontend/js/app.js
git commit -m "feat(frontend): registrar novas paginas e atualizar tab Ocorrencia para Relatorios"
```

---

## Task 8: Remover `ocorrencia-upload.js`

**Files:**
- Delete: `frontend/js/pages/ocorrencia-upload.js`

**Contexto:** O arquivo não é mais referenciado nem usado. Remover para evitar dead code.

**Step 1: Confirmar que não há mais referências**

```bash
grep -r "ocorrencia-upload\|renderOcorrenciaUpload" frontend/
```
Esperado: sem resultados.

**Step 2: Remover o arquivo**

```bash
git rm frontend/js/pages/ocorrencia-upload.js
git commit -m "chore(frontend): remover ocorrencia-upload.js substituido por ocorrencias.js"
```

---

## Task 9: Verificação final

**Step 1: Rodar todos os testes**

```bash
make test
```
Esperado: todos PASS.

**Step 2: Lint completo**

```bash
make lint
```
Esperado: sem erros.

**Step 3: Smoke test manual**

1. `make dev` — subir ambiente local
2. Fazer login
3. Clicar tab "Relatórios" → lista de abordagens aparece
4. Clicar em uma abordagem → detalhe abre com pessoas, veículos, mapa
5. Clicar em um abordado → ficha da pessoa abre
6. Voltar → enviar RAP PDF → ocorrência aparece vinculada
7. Adicionar uma mídia (foto ou vídeo) → thumbnail aparece no grid

**Step 4: Commit de encerramento se necessário**

```bash
git add -A
git commit -m "feat: feature Relatorio de Abordagens completa"
```
