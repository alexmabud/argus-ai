# Data da Ocorrência — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar campo `data_ocorrencia` (DATE) à ocorrência para registrar quando o fato aconteceu, separado da data de cadastro (`criado_em`).

**Architecture:** Nova coluna `data_ocorrencia DATE NOT NULL` na tabela `ocorrencias`, exposta via schema Pydantic e recebida como `Form(...)` no endpoint de criação. A busca por data (`/buscar?data=`) passa a filtrar por `data_ocorrencia` em vez de `criado_em`. Frontend exibe as duas datas nas listas.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, FastAPI Form params, Pydantic v2, Alpine.js

---

### Task 1: Modelo + Migration

**Files:**
- Modify: `app/models/ocorrencia.py`
- Create: nova migration Alembic (gerada automaticamente)
- Modify: `tests/conftest.py:297-306`

**Step 1: Atualizar o modelo**

Em `app/models/ocorrencia.py`, adicionar `date` e `Date` aos imports e o novo campo após `nomes_envolvidos`:

```python
from datetime import date  # adicionar ao topo junto com os outros imports

from sqlalchemy import Boolean, Date, ForeignKey, String, Text  # adicionar Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

# na classe Ocorrencia, após nomes_envolvidos:
data_ocorrencia: Mapped[date] = mapped_column(Date, nullable=False)
```

Atualizar a docstring da classe, seção `Attributes`:
```
data_ocorrencia: Data real do fato ocorrido (pode diferir de criado_em).
```

**Step 2: Gerar migration**

```bash
python -m alembic revision --autogenerate -m "ocorrencia_data_ocorrencia"
```

Abrir o arquivo gerado em `alembic/versions/`. Verificar que o `upgrade()` contém algo como:
```python
op.add_column('ocorrencias', sa.Column('data_ocorrencia', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')))
```

**IMPORTANTE:** Adicionar `server_default=sa.text('CURRENT_DATE')` na chamada `add_column` se não foi gerado automaticamente — necessário para linhas existentes. Também adicionar `op.alter_column('ocorrencias', 'data_ocorrencia', server_default=None)` no `upgrade()` após `add_column`, para remover o default do banco depois de preencher as linhas existentes (opcional, mas limpo).

Adicionar docstring Google Style ao arquivo de migration gerado (ver outros arquivos em `alembic/versions/` como referência).

**Step 3: Aplicar migration**

```bash
python -m alembic upgrade head
```

Esperado: sem erros.

**Step 4: Atualizar fixture de ocorrência em conftest**

Em `tests/conftest.py`, na fixture `ocorrencia` (linha ~297), adicionar `data_ocorrencia`:

```python
from datetime import UTC, date, datetime  # garantir que date está importado

o = Ocorrencia(
    numero_ocorrencia="RAP 2026/000001",
    abordagem_id=abordagem.id,
    arquivo_pdf_url="https://r2.example.com/pdfs/test.pdf",
    texto_extraido="Abordado: Carlos Eduardo Souza, CPF 123.456.789-00. Conduzido à delegacia.",
    processada=True,
    usuario_id=usuario.id,
    guarnicao_id=guarnicao.id,
    data_ocorrencia=date.today(),  # <-- adicionar
)
```

**Step 5: Rodar testes para confirmar sem regressão**

```bash
python -m pytest tests/ -x -q
```

Esperado: todos passando (ou falhas apenas relacionadas ao novo campo ainda não exposto na API).

**Step 6: Commit**

```bash
git add app/models/ocorrencia.py alembic/versions/ tests/conftest.py
git commit -m "feat(ocorrencia): adicionar campo data_ocorrencia ao modelo e migration"
```

---

### Task 2: Schema + API + Service + Repositório (TDD)

**Files:**
- Modify: `app/schemas/ocorrencia.py`
- Modify: `app/api/v1/ocorrencias.py`
- Modify: `app/services/ocorrencia_service.py`
- Modify: `app/repositories/ocorrencia_repo.py`
- Modify: `tests/integration/test_api_ocorrencias.py`

**Step 1: Escrever testes que vão falhar**

Em `tests/integration/test_api_ocorrencias.py`, adicionar ao final da classe `TestBuscarOcorrencias`:

```python
async def test_busca_por_data_ocorrencia_retorna_ocorrencia(
    self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
):
    """Testa que busca por data filtra por data_ocorrencia (não criado_em).

    Args:
        client: Cliente HTTP assincrónico.
        auth_headers: Headers com Bearer token válido.
        ocorrencia: Fixture com data_ocorrencia=hoje.
    """
    from datetime import UTC, date, datetime

    hoje = date.today().isoformat()
    response = await client.get(
        f"/api/v1/ocorrencias/buscar?data={hoje}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["data_ocorrencia"] == hoje
```

Adicionar também uma classe nova para testar o campo no endpoint de criação. Como criar via API requer upload de PDF real (muito complexo para teste de integração), vamos testar via schema diretamente:

Em `tests/unit/test_schemas_ocorrencia.py` (arquivo existente), adicionar:

```python
def test_ocorrencia_read_expoe_data_ocorrencia():
    """Testa que OcorrenciaRead expõe o campo data_ocorrencia."""
    from datetime import date, datetime, timezone
    from app.schemas.ocorrencia import OcorrenciaRead

    now = datetime.now(timezone.utc)
    schema = OcorrenciaRead(
        id=1,
        numero_ocorrencia="RAP 2026/000001",
        abordagem_id=None,
        arquivo_pdf_url="https://example.com/file.pdf",
        processada=False,
        nomes_envolvidos=None,
        data_ocorrencia=date(2026, 3, 7),
        usuario_id=1,
        guarnicao_id=1,
        criado_em=now,
        atualizado_em=now,
    )
    assert schema.data_ocorrencia == date(2026, 3, 7)
```

**Step 2: Rodar testes para confirmar que falham**

```bash
python -m pytest tests/unit/test_schemas_ocorrencia.py::test_ocorrencia_read_expoe_data_ocorrencia -v
```

Esperado: FAIL com `ValidationError` ou `TypeError` (campo não existe ainda no schema).

**Step 3: Atualizar schema**

Em `app/schemas/ocorrencia.py`:

```python
from datetime import date, datetime  # adicionar date

# Em OcorrenciaRead, após processada:
data_ocorrencia: date
```

Atualizar docstring da classe `OcorrenciaRead`:
```
data_ocorrencia: Data real do fato ocorrido (informada no cadastro).
```

**Step 4: Rodar o teste unitário — deve passar**

```bash
python -m pytest tests/unit/test_schemas_ocorrencia.py -v
```

Esperado: todos passando.

**Step 5: Atualizar o endpoint de criação**

Em `app/api/v1/ocorrencias.py`, adicionar parâmetro ao `criar_ocorrencia` (após `nomes_envolvidos`):

```python
from datetime import date  # adicionar ao topo

# no endpoint criar_ocorrencia, após nomes_envolvidos:
data_ocorrencia: date = Form(..., description="Data real do fato (YYYY-MM-DD)"),
```

Atualizar a chamada ao service:
```python
ocorrencia = await service.criar(
    numero_ocorrencia=numero_ocorrencia,
    abordagem_id=abordagem_id,
    nomes_envolvidos=nomes_envolvidos,
    data_ocorrencia=data_ocorrencia,  # <-- adicionar
    arquivo_pdf=pdf_bytes,
    filename=arquivo_pdf.filename or "ocorrencia.pdf",
    usuario_id=user.id,
    guarnicao_id=user.guarnicao_id,
)
```

Atualizar docstring do endpoint (seção Args):
```
data_ocorrencia: Data real do fato ocorrido (formato YYYY-MM-DD).
```

**Step 6: Atualizar o service**

Em `app/services/ocorrencia_service.py`, método `criar()`:

```python
from datetime import date  # adicionar ao topo

# Adicionar parâmetro após nomes_envolvidos:
async def criar(
    self,
    numero_ocorrencia: str,
    abordagem_id: int | None,
    nomes_envolvidos: str | None,
    data_ocorrencia: date,          # <-- adicionar
    arquivo_pdf: bytes,
    filename: str,
    usuario_id: int,
    guarnicao_id: int,
) -> Ocorrencia:

# Passar ao construtor Ocorrencia:
ocorrencia = Ocorrencia(
    numero_ocorrencia=numero_ocorrencia,
    abordagem_id=abordagem_id,
    nomes_envolvidos=nomes_envolvidos,
    data_ocorrencia=data_ocorrencia,  # <-- adicionar
    arquivo_pdf_url=url,
    processada=False,
    usuario_id=usuario_id,
    guarnicao_id=guarnicao_id,
)
```

Atualizar docstring de `criar()` (seção Args):
```
data_ocorrencia: Data real do fato ocorrido.
```

**Step 7: Atualizar o repositório**

Em `app/repositories/ocorrencia_repo.py`, método `buscar()`, substituir o bloco `if data:`:

```python
# ANTES:
if data:
    data_inicio = datetime.combine(data, time.min).replace(tzinfo=UTC)
    data_fim = datetime.combine(data, time.max).replace(tzinfo=UTC)
    query = query.where(
        Ocorrencia.criado_em >= data_inicio,
        Ocorrencia.criado_em <= data_fim,
    )

# DEPOIS:
if data:
    query = query.where(Ocorrencia.data_ocorrencia == data)
```

Remover imports que ficaram sem uso: `UTC`, `datetime`, `time` (verificar se ainda usados em outro lugar no arquivo — neste arquivo eram só usados no bloco `if data:`). Manter `date` que ainda é usado na assinatura.

Atualizar docstring de `buscar()`:
- Mudar "Data exata de criação da ocorrência." para "Data exata do fato ocorrido."

**Step 8: Rodar todos os testes de integração de ocorrências**

```bash
python -m pytest tests/integration/test_api_ocorrencias.py -v
```

Esperado: todos passando, incluindo `test_busca_por_data_ocorrencia_retorna_ocorrencia`.

**Step 9: Commit**

```bash
git add app/schemas/ocorrencia.py app/api/v1/ocorrencias.py \
        app/services/ocorrencia_service.py app/repositories/ocorrencia_repo.py \
        tests/integration/test_api_ocorrencias.py tests/unit/test_schemas_ocorrencia.py
git commit -m "feat(ocorrencia): expor e receber data_ocorrencia no schema, API e service"
```

---

### Task 3: Frontend

**Files:**
- Modify: `frontend/js/pages/ocorrencia-upload.js`

**Step 1: Adicionar estado e campo ao formulário**

Em `ocorrenciaUploadPage()`, adicionar estado (junto com `novoEnvolvido` e `envolvidos`):

```js
dataOcorrencia: new Date().toISOString().split("T")[0],  // hoje em YYYY-MM-DD
```

No template `renderOcorrenciaUpload()`, adicionar campo após o campo de abordagem e antes do campo de arquivo PDF:

```html
<!-- Data da ocorrência -->
<div>
  <label class="block text-sm text-slate-300 mb-1">Data da Ocorrência</label>
  <input type="date" x-model="dataOcorrencia" required>
</div>
```

**Step 2: Enviar data_ocorrencia no submit**

No método `submit()`, dentro do bloco `FormData`, após `nomes_envolvidos`:

```js
form.append("data_ocorrencia", this.dataOcorrencia);
```

Resetar o campo no `submit()` após sucesso (junto com os demais resets):

```js
this.dataOcorrencia = new Date().toISOString().split("T")[0];
```

**Step 3: Exibir as duas datas nas listas**

Criar uma função helper no objeto Alpine para formatar datas:

```js
formatDate(isoString) {
  if (!isoString) return "";
  // Suporta tanto "2026-03-07" (DATE) quanto "2026-03-07T..." (DATETIME)
  const d = new Date(isoString + (isoString.includes("T") ? "" : "T00:00:00"));
  return d.toLocaleDateString("pt-BR");
},
```

**Na lista de ocorrências recentes** (template x-for que renderiza `oc in ocorrencias`), substituir a linha de data única:

```html
<!-- ANTES -->
<p class="text-xs text-slate-500" x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>

<!-- DEPOIS -->
<p class="text-xs text-slate-500"
   x-text="'Ocorrido em ' + formatDate(oc.data_ocorrencia) + ' · Registrado em ' + formatDate(oc.criado_em)"></p>
```

**Nos resultados de busca** (template x-for que renderiza `oc in (resultadosBusca || [])`), aplicar a mesma substituição.

**Step 4: Teste manual**

1. Abrir `http://localhost:8000` no browser
2. Navegar para "Registrar Ocorrência"
3. Verificar que o campo "Data da Ocorrência" aparece pré-preenchido com hoje
4. Alterar a data para uma data passada (ex: 07/03/2026)
5. Preencher os outros campos e enviar
6. Verificar que na lista aparece "Ocorrido em 07/03/2026 · Registrado em 09/03/2026"
7. Usar a busca por data com 07/03/2026 e verificar que a ocorrência aparece

**Step 5: Commit**

```bash
git add frontend/js/pages/ocorrencia-upload.js
git commit -m "feat(frontend): adicionar campo data_ocorrencia no formulário e exibir nas listas"
```
