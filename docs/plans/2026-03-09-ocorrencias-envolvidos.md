# Ocorrências — Nomes dos Envolvidos

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar campo de nomes dos envolvidos (chips de texto livre) no cadastro de ocorrência, exibir os nomes nas listas, e incluí-los na busca por nome.

**Architecture:** Nova coluna `nomes_envolvidos TEXT` nullable em `ocorrencias`, armazenada como pipe-separated string (`"João|Maria"`). Schema Pydantic faz parse para `list[str]`. Frontend Alpine.js usa array reativo com chips visuais. Busca por nome passa a usar OR em `texto_extraido` e `nomes_envolvidos`.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, FastAPI Form, Pydantic field_validator, Alpine.js, Tailwind CSS

---

### Task 1: Model + Schema + Migration

**Files:**
- Modify: `app/models/ocorrencia.py`
- Modify: `app/schemas/ocorrencia.py`
- Create: migration via `python -m alembic revision --autogenerate -m "ocorrencia_nomes_envolvidos"`

**Contexto:**
- `app/models/ocorrencia.py` tem a classe `Ocorrencia(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin)` — adicionar campo após `texto_extraido`
- `app/schemas/ocorrencia.py` tem `OcorrenciaRead` com `model_config = {"from_attributes": True}` — adicionar campo com validator
- Pydantic v2 usa `@field_validator("campo", mode="before")` com `@classmethod`

**Step 1: Adicionar campo no model**

Em `app/models/ocorrencia.py`, após a linha `texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)`, adicionar:

```python
nomes_envolvidos: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Também atualizar a docstring da classe, no bloco `Attributes:`:
```
        nomes_envolvidos: Nomes dos envolvidos separados por pipe (opcional).
```

**Step 2: Atualizar schema `OcorrenciaRead`**

Em `app/schemas/ocorrencia.py`, adicionar import no topo:
```python
from pydantic import BaseModel, Field, field_validator
```

No `OcorrenciaRead`, adicionar campo após `processada`:
```python
    nomes_envolvidos: list[str] = Field(default_factory=list)

    @field_validator("nomes_envolvidos", mode="before")
    @classmethod
    def parse_nomes(cls, v: object) -> list[str]:
        """Converte pipe-string em lista de nomes.

        Args:
            v: Valor bruto do banco (str com pipe, None, ou já list).

        Returns:
            Lista de nomes sem espaços extras.
        """
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        return [n.strip() for n in str(v).split("|") if n.strip()]
```

Atualizar docstring `OcorrenciaRead` no bloco `Attributes:`:
```
        nomes_envolvidos: Lista de nomes dos envolvidos (texto livre).
```

**Step 3: Gerar e aplicar migration**

```bash
python -m alembic revision --autogenerate -m "ocorrencia_nomes_envolvidos"
python -m alembic upgrade head
```

Verificar que o arquivo gerado em `alembic/versions/` contém `op.add_column('ocorrencias', sa.Column('nomes_envolvidos', sa.Text(), nullable=True))`.

**Step 4: Escrever teste unitário do validator**

No arquivo `tests/unit/test_schemas_ocorrencia.py` (criar se não existir):

```python
"""Testes unitários dos schemas de Ocorrência."""

from datetime import datetime
from app.schemas.ocorrencia import OcorrenciaRead


def _base_data(**kwargs) -> dict:
    """Retorna dados mínimos válidos para OcorrenciaRead."""
    return {
        "id": 1,
        "numero_ocorrencia": "RAP 2026/000001",
        "abordagem_id": None,
        "arquivo_pdf_url": "https://r2.example.com/test.pdf",
        "processada": False,
        "usuario_id": 1,
        "guarnicao_id": 1,
        "criado_em": datetime(2026, 1, 1),
        "atualizado_em": datetime(2026, 1, 1),
        **kwargs,
    }


def test_parse_nomes_none():
    """None vira lista vazia."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=None))
    assert oc.nomes_envolvidos == []


def test_parse_nomes_vazio():
    """String vazia vira lista vazia."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=""))
    assert oc.nomes_envolvidos == []


def test_parse_nomes_um():
    """String com um nome vira lista de um elemento."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos="João da Silva"))
    assert oc.nomes_envolvidos == ["João da Silva"]


def test_parse_nomes_multiplos():
    """String pipe-separated vira lista de nomes."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos="João da Silva|Maria Souza|Pedro Lima"))
    assert oc.nomes_envolvidos == ["João da Silva", "Maria Souza", "Pedro Lima"]


def test_parse_nomes_espacos_extras():
    """Espaços ao redor do pipe são removidos."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=" João  | Maria "))
    assert oc.nomes_envolvidos == ["João", "Maria"]
```

**Step 5: Rodar os testes unitários**

```bash
python -m pytest tests/unit/test_schemas_ocorrencia.py -v
```

Esperado: 5 testes PASS.

**Step 6: Commit**

```bash
git add app/models/ocorrencia.py app/schemas/ocorrencia.py alembic/versions/ tests/unit/test_schemas_ocorrencia.py
git commit -m "feat(ocorrencias): adicionar campo nomes_envolvidos ao model e schema"
```

---

### Task 2: Service + Router

**Files:**
- Modify: `app/services/ocorrencia_service.py`
- Modify: `app/api/v1/ocorrencias.py`

**Contexto:**
- `service.criar()` tem assinatura `(numero_ocorrencia, abordagem_id, arquivo_pdf, filename, usuario_id, guarnicao_id)` — adicionar `nomes_envolvidos`
- Router `POST /ocorrencias/` usa `Form(...)` para cada campo — adicionar o novo
- O router já importa `Form` de fastapi

**Step 1: Atualizar `OcorrenciaService.criar()`**

Em `app/services/ocorrencia_service.py`, na assinatura do método `criar`, adicionar parâmetro após `abordagem_id`:

```python
    async def criar(
        self,
        numero_ocorrencia: str,
        abordagem_id: int | None,
        nomes_envolvidos: str | None,
        arquivo_pdf: bytes,
        filename: str,
        usuario_id: int,
        guarnicao_id: int,
    ) -> Ocorrencia:
```

Atualizar docstring `Args:`:
```
            nomes_envolvidos: Nomes dos envolvidos separados por pipe (opcional).
```

Atualizar a criação do objeto `Ocorrencia` para incluir o campo:
```python
        ocorrencia = Ocorrencia(
            numero_ocorrencia=numero_ocorrencia,
            abordagem_id=abordagem_id,
            nomes_envolvidos=nomes_envolvidos,
            arquivo_pdf_url=url,
            processada=False,
            usuario_id=usuario_id,
            guarnicao_id=guarnicao_id,
        )
```

**Step 2: Atualizar router `POST /ocorrencias/`**

Em `app/api/v1/ocorrencias.py`, na função `criar_ocorrencia`, adicionar parâmetro após `abordagem_id`:

```python
    nomes_envolvidos: str | None = Form(None),
```

Atualizar docstring `Args:`:
```
        nomes_envolvidos: Nomes dos envolvidos separados por pipe (opcional).
```

Atualizar a chamada ao service:
```python
    ocorrencia = await service.criar(
        numero_ocorrencia=numero_ocorrencia,
        abordagem_id=abordagem_id,
        nomes_envolvidos=nomes_envolvidos,
        arquivo_pdf=pdf_bytes,
        filename=arquivo_pdf.filename or "ocorrencia.pdf",
        usuario_id=user.id,
        guarnicao_id=user.guarnicao_id,
    )
```

**Step 3: Commit**

```bash
git add app/services/ocorrencia_service.py app/api/v1/ocorrencias.py
git commit -m "feat(ocorrencias): aceitar nomes_envolvidos no service e router"
```

---

### Task 3: Repository — busca por nome em nomes_envolvidos

**Files:**
- Modify: `app/repositories/ocorrencia_repo.py`
- Modify: `tests/integration/test_api_ocorrencias.py`

**Contexto:**
- `OcorrenciaRepository.buscar()` em `app/repositories/ocorrencia_repo.py` faz ILIKE em `texto_extraido` quando `nome` é passado
- SQLAlchemy `or_` é importado de `sqlalchemy`
- A fixture `ocorrencia` em `tests/conftest.py` cria com `abordagem_id=abordagem.id` — ao adicionar `nomes_envolvidos=None`, não quebra (nullable)

**Step 1: Escrever teste de busca por nome em nomes_envolvidos**

Ao final de `tests/integration/test_api_ocorrencias.py`, adicionar:

```python
    async def test_busca_por_nome_em_nomes_envolvidos(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
        guarnicao, usuario
    ):
        """Testa que busca por nome encontra ocorrência pelo campo nomes_envolvidos.

        Cria ocorrência SEM texto extraído mas COM nomes_envolvidos,
        e verifica que a busca por nome a encontra.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão do banco de dados.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        oc = Ocorrencia(
            numero_ocorrencia="RAP 2026/000002",
            arquivo_pdf_url="https://r2.example.com/pdfs/test2.pdf",
            nomes_envolvidos="Fulano de Tal|Ciclano Silva",
            processada=False,
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(oc)
        await db_session.flush()

        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Fulano de Tal",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000002"
        assert "Fulano de Tal" in data[0]["nomes_envolvidos"]
```

**Step 2: Rodar o teste para verificar que falha**

```bash
python -m pytest tests/integration/test_api_ocorrencias.py::TestBuscarOcorrencias::test_busca_por_nome_em_nomes_envolvidos -v
```

Esperado: FAIL — ocorrência não encontrada pela busca atual.

**Step 3: Atualizar `OcorrenciaRepository.buscar()`**

Em `app/repositories/ocorrencia_repo.py`, adicionar `or_` no import:

```python
from sqlalchemy import or_, select
```

Substituir o bloco `if nome:` por:

```python
        if nome:
            nome_escaped = _escape_like(nome)
            query = query.where(
                or_(
                    Ocorrencia.texto_extraido.ilike(f"%{nome_escaped}%"),
                    Ocorrencia.nomes_envolvidos.ilike(f"%{nome_escaped}%"),
                )
            )
```

**Atenção:** remover o filtro `Ocorrencia.processada == True` que estava dentro do `if nome`. A busca por nome em `nomes_envolvidos` deve funcionar mesmo em ocorrências não processadas (que ainda não têm `texto_extraido`). O filtro de `processada` era necessário apenas para garantir que `texto_extraido` existisse, mas `nomes_envolvidos` é preenchido no momento do cadastro. A query nova com OR já trata isso: se `texto_extraido` for NULL, o ILIKE nele retorna NULL (falsy), e o OR avalia `nomes_envolvidos`.

**Step 4: Atualizar docstring do método `buscar`**

No parâmetro `nome` do Args:
```
            nome: Trecho do nome a buscar no texto extraído do PDF ou nos nomes dos envolvidos.
```

**Step 5: Rodar todos os testes de ocorrências**

```bash
python -m pytest tests/integration/test_api_ocorrencias.py -v
```

Esperado: todos PASS (incluindo o novo).

**Step 6: Commit**

```bash
git add app/repositories/ocorrencia_repo.py tests/integration/test_api_ocorrencias.py
git commit -m "feat(ocorrencias): busca por nome inclui campo nomes_envolvidos"
```

---

### Task 4: Frontend — chips no formulário e exibição nas listas

**Files:**
- Modify: `frontend/js/pages/ocorrencia-upload.js`

**Contexto do arquivo atual:**
- `renderOcorrenciaUpload()` retorna o template HTML (linhas 7–131)
- `ocorrenciaUploadPage()` retorna o objeto Alpine.js com estado e métodos (linhas 134–209)
- O formulário de cadastro está dentro do `<div class="card space-y-4">` (linhas 12–32)
- O campo de arquivo PDF termina na linha ~31
- O `submit()` começa na linha 165, faz `form.append(...)` e chama `api.request()`
- Reset após sucesso nas linhas 178–180
- Cards da busca: linhas 77–95 (cada card tem nome, data, chip, botão PDF)
- Cards da lista recente: linhas 102–121 (mesma estrutura)

**Step 1: Adicionar estado Alpine.js**

No objeto retornado por `ocorrenciaUploadPage()`, após `abordagemId: null,` adicionar:

```js
    novoEnvolvido: "",
    envolvidos: [],
```

**Step 2: Adicionar métodos no objeto Alpine.js**

No objeto, após `formatSize(bytes) { ... },` e antes de `async submit() {`, adicionar:

```js
    adicionarEnvolvido() {
      const nome = this.novoEnvolvido.trim();
      if (nome && !this.envolvidos.includes(nome)) {
        this.envolvidos.push(nome);
      }
      this.novoEnvolvido = "";
    },

    removerEnvolvido(index) {
      this.envolvidos.splice(index, 1);
    },
```

**Step 3: Atualizar `submit()` — enviar nomes e resetar**

Dentro de `submit()`, após `if (this.abordagemId) form.append("abordagem_id", this.abordagemId);` e antes de `await api.request(...)`, adicionar:

```js
        if (this.envolvidos.length > 0) {
          form.append("nomes_envolvidos", this.envolvidos.join("|"));
        }
```

No bloco de reset após sucesso (após `this.abordagemId = null;`), adicionar:

```js
        this.envolvidos = [];
        this.novoEnvolvido = "";
```

**Step 4: Adicionar bloco Envolvidos no template HTML**

Na função `renderOcorrenciaUpload()`, dentro do `<div class="card space-y-4">`, após o bloco do campo Arquivo PDF (que termina com `</div>` do bloco `<div>` do arquivo), adicionar o novo bloco:

```html

        <!-- Envolvidos -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">Envolvidos</label>
          <div class="flex gap-2">
            <input type="text" x-model="novoEnvolvido"
                   placeholder="Nome do envolvido"
                   @keydown.enter.prevent="adicionarEnvolvido()"
                   class="flex-1">
            <button type="button" @click="adicionarEnvolvido()"
                    class="btn btn-secondary px-3 shrink-0">+ Adicionar</button>
          </div>
          <div x-show="envolvidos.length > 0" class="flex flex-wrap gap-1 mt-2">
            <template x-for="(nome, i) in envolvidos" :key="i">
              <span class="flex items-center gap-1 text-xs bg-slate-700 text-slate-200 px-2 py-0.5 rounded-full">
                <span x-text="nome"></span>
                <button type="button" @click="removerEnvolvido(i)"
                        class="text-slate-400 hover:text-red-400 leading-none ml-0.5">×</button>
              </span>
            </template>
          </div>
        </div>
```

**Step 5: Adicionar linha de nomes nos cards da busca**

Na seção de resultados de busca (em torno da linha 80), dentro de `<div>` com nome e data, após `<p class="text-xs text-slate-500" ...>` (a linha da data), adicionar:

```html
                  <p x-show="oc.nomes_envolvidos && oc.nomes_envolvidos.length > 0"
                     class="text-xs text-slate-400 mt-0.5"
                     x-text="oc.nomes_envolvidos.join(' · ')"></p>
```

**Step 6: Adicionar linha de nomes nos cards da lista recente**

Na seção "Lista de ocorrências recentes" (em torno da linha 106), dentro de `<div>` com nome e data, após `<p class="text-xs text-slate-500" ...>` (a linha da data), adicionar o mesmo elemento:

```html
                  <p x-show="oc.nomes_envolvidos && oc.nomes_envolvidos.length > 0"
                     class="text-xs text-slate-400 mt-0.5"
                     x-text="oc.nomes_envolvidos.join(' · ')"></p>
```

**Step 7: Verificar visualmente**

1. Abrir `http://localhost:8000/#ocorrencia-upload`
2. No formulário: digitar um nome no campo Envolvidos, clicar "+ Adicionar" → chip aparece
3. Clicar `×` no chip → chip removido
4. Digitar nome e apertar Enter → chip adicionado (keydown.enter)
5. Cadastrar ocorrência com 2 nomes → após sucesso, chips resetados
6. Na lista recente, o card deve mostrar os nomes abaixo da data

**Step 8: Commit**

```bash
git add frontend/js/pages/ocorrencia-upload.js
git commit -m "feat(frontend): adicionar chips de envolvidos no cadastro e nomes nas listas de ocorrências"
```
