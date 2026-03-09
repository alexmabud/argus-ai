# Ocorrências — Nomes dos Envolvidos (Design)

**Data:** 2026-03-09
**Status:** Aprovado

## Objetivo

Adicionar campo de nomes dos envolvidos no cadastro de ocorrência (texto livre, múltiplos nomes via chips), exibir os nomes nas listas de ocorrências (recentes e busca), e incluir os nomes na busca por nome existente.

## Decisões de Design

- **Texto livre** — sem vínculo com a tabela `pessoas`; policial digita o nome no momento do cadastro
- **UX chips** — input + botão Adicionar gera tags removíveis; melhor que textarea ou campo único para múltiplos nomes
- **Separador pipe `|`** — nomes armazenados como `"João da Silva|Maria Souza"` no banco; pipe evita ambiguidade com vírgula em nomes compostos
- **API retorna `list[str]`** — o parse do pipe-string é feito no schema Pydantic, a API expõe lista limpa

## Arquitetura

### Backend

**Model** (`app/models/ocorrencia.py`):
```python
nomes_envolvidos: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Schema** (`app/schemas/ocorrencia.py`):
- `OcorrenciaRead`: adicionar `nomes_envolvidos: list[str]` com `@field_validator("nomes_envolvidos", mode="before")` que converte `None` → `[]` e `"A|B"` → `["A", "B"]`

**Router** (`app/api/v1/ocorrencias.py`):
- `POST /`: adicionar `nomes_envolvidos: str | None = Form(None)`
- Passa para `service.criar()`

**Service** (`app/services/ocorrencia_service.py`):
- `criar()`: recebe `nomes_envolvidos: str | None`, salva no model

**Repository** (`app/repositories/ocorrencia_repo.py`):
- `buscar()` com filtro `nome`: além de `texto_extraido.ilike(...)`, adicionar OR com `nomes_envolvidos.ilike(...)`

**Migration**: `alembic revision --autogenerate -m "ocorrencia_nomes_envolvidos"`

### Frontend (`frontend/js/pages/ocorrencia-upload.js`)

**Estado Alpine.js** (adicionar ao objeto):
```js
novoEnvolvido: "",
envolvidos: [],
```

**Métodos**:
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

**Submit** — antes do `api.request(...)`:
```js
if (this.envolvidos.length > 0) {
  form.append("nomes_envolvidos", this.envolvidos.join("|"));
}
```

**Reset após sucesso**:
```js
this.envolvidos = [];
this.novoEnvolvido = "";
```

**Template — bloco Envolvidos no formulário** (após campo Arquivo PDF):
```html
<!-- Envolvidos -->
<div>
  <label class="block text-sm text-slate-300 mb-1">Envolvidos</label>
  <div class="flex gap-2">
    <input type="text" x-model="novoEnvolvido" placeholder="Nome do envolvido"
           @keydown.enter.prevent="adicionarEnvolvido()" class="flex-1">
    <button type="button" @click="adicionarEnvolvido()"
            class="btn btn-secondary px-3">+ Adicionar</button>
  </div>
  <div x-show="envolvidos.length > 0" class="flex flex-wrap gap-1 mt-2">
    <template x-for="(nome, i) in envolvidos" :key="i">
      <span class="flex items-center gap-1 text-xs bg-slate-700 text-slate-200 px-2 py-0.5 rounded-full">
        <span x-text="nome"></span>
        <button type="button" @click="removerEnvolvido(i)"
                class="text-slate-400 hover:text-red-400 leading-none">×</button>
      </span>
    </template>
  </div>
</div>
```

**Template — linha de nomes nos cards** (listas recente e busca, abaixo da data):
```html
<p x-show="oc.nomes_envolvidos && oc.nomes_envolvidos.length > 0"
   class="text-xs text-slate-400 mt-0.5"
   x-text="oc.nomes_envolvidos.join(' · ')"></p>
```

## Fluxo de Dados

```
Frontend chips → join("|") → FormData "nomes_envolvidos"
  → router Form(...) → service.criar(nomes_envolvidos=...)
  → Ocorrencia.nomes_envolvidos = "João|Maria"
  → OcorrenciaRead.nomes_envolvidos = ["João", "Maria"]  (parse no schema)
  → frontend list: oc.nomes_envolvidos.join(" · ")
```

## Busca por Nome (melhoria)

Query atual:
```python
Ocorrencia.texto_extraido.ilike(f"%{nome}%")
```

Nova query:
```python
or_(
    Ocorrencia.texto_extraido.ilike(f"%{nome}%"),
    Ocorrencia.nomes_envolvidos.ilike(f"%{nome}%"),
)
```

Requer `from sqlalchemy import or_` no repo.
