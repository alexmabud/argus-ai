# Campo `nome_mae` em Pessoa — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar campo opcional `nome_mae` ao cadastro de Pessoa, com índice GIN trgm preparado para busca futura e formulários atualizados em Abordagem Nova e Consulta IA.

**Architecture:** Nova coluna `nome_mae VARCHAR(300)` em `pessoas` com índice GIN `gin_trgm_ops`. Schema Pydantic, service e frontend passam a propagar o campo. Exibição em cards de resultado da consulta. Sem implementação de busca textual por nome_mae neste ciclo (índice fica preparado).

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, Pydantic v2, Alpine.js, pg_trgm.

**Design source:** [docs/plans/2026-04-17-nome-mae-pessoa-design.md](2026-04-17-nome-mae-pessoa-design.md)

---

## Task 1: Model `Pessoa` — adicionar campo `nome_mae`

**Files:**
- Modify: `app/models/pessoa.py`
- Test: `tests/unit/test_pessoa_model.py` (criar se não existir) OU adicionar a um existente

**Step 1: Escrever teste falho**

Localizar ou criar `tests/unit/test_pessoa_model.py` com o seguinte teste:

```python
def test_pessoa_tem_campo_nome_mae():
    """Pessoa deve aceitar nome_mae opcional (nullable)."""
    from app.models.pessoa import Pessoa

    p = Pessoa(nome="Fulano de Tal", nome_mae="Maria das Dores", guarnicao_id=1)
    assert p.nome_mae == "Maria das Dores"

    p2 = Pessoa(nome="Ciclano", guarnicao_id=1)
    assert p2.nome_mae is None
```

**Step 2: Rodar teste e verificar falha**

Run: `pytest tests/unit/test_pessoa_model.py::test_pessoa_tem_campo_nome_mae -v`
Expected: FAIL com `TypeError: 'nome_mae' is an invalid keyword argument for Pessoa`

**Step 3: Adicionar campo ao model**

Em [app/models/pessoa.py:57](app/models/pessoa.py#L57), logo após a linha do `apelido`:

```python
apelido: Mapped[str | None] = mapped_column(String(100), nullable=True)
nome_mae: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
```

Adicionar índice GIN trgm em `__table_args__` ([app/models/pessoa.py:84-92](app/models/pessoa.py#L84-L92)):

```python
__table_args__ = (
    Index(
        "idx_pessoa_nome_trgm",
        "nome",
        postgresql_using="gin",
        postgresql_ops={"nome": "gin_trgm_ops"},
    ),
    Index(
        "idx_pessoa_nome_mae_trgm",
        "nome_mae",
        postgresql_using="gin",
        postgresql_ops={"nome_mae": "gin_trgm_ops"},
    ),
    Index("idx_pessoa_guarnicao", "guarnicao_id"),
)
```

Atualizar docstring da classe (seção `Attributes`) adicionando a linha:
```
nome_mae: Nome da mãe (opcional, busca fuzzy via pg_trgm preparada).
```

**Step 4: Rodar teste e verificar sucesso**

Run: `pytest tests/unit/test_pessoa_model.py::test_pessoa_tem_campo_nome_mae -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/models/pessoa.py tests/unit/test_pessoa_model.py
git commit -m "feat(pessoa): adicionar campo nome_mae ao model com indice GIN trgm"
```

---

## Task 2: Schemas Pydantic — adicionar `nome_mae`

**Files:**
- Modify: `app/schemas/pessoa.py`
- Test: `tests/unit/test_pessoa_schemas.py` (criar se não existir)

**Step 1: Escrever teste falho**

```python
from app.schemas.pessoa import PessoaCreate, PessoaUpdate


def test_pessoa_create_aceita_nome_mae():
    p = PessoaCreate(nome="Fulano", nome_mae="Maria")
    assert p.nome_mae == "Maria"


def test_pessoa_create_nome_mae_opcional():
    p = PessoaCreate(nome="Fulano")
    assert p.nome_mae is None


def test_pessoa_create_nome_mae_max_length():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PessoaCreate(nome="Fulano", nome_mae="x" * 301)


def test_pessoa_update_aceita_nome_mae():
    p = PessoaUpdate(nome_mae="Nova Mae")
    assert p.nome_mae == "Nova Mae"
```

**Step 2: Rodar testes e verificar falha**

Run: `pytest tests/unit/test_pessoa_schemas.py -v`
Expected: FAIL (campo não existe)

**Step 3: Adicionar `nome_mae` aos schemas**

Em [app/schemas/pessoa.py](app/schemas/pessoa.py):

**`PessoaCreate`** (após linha 31, após `apelido`):
```python
apelido: str | None = Field(None, max_length=100)
nome_mae: str | None = Field(None, max_length=300)
observacoes: str | None = None
```
Atualizar docstring (seção `Attributes`) adicionando:
```
nome_mae: Nome da mãe (opcional, até 300 caracteres).
```

**`PessoaUpdate`** (após linha 51):
```python
apelido: str | None = Field(None, max_length=100)
nome_mae: str | None = Field(None, max_length=300)
observacoes: str | None = None
```
Atualizar docstring idem.

**`PessoaRead`** (após linha 78):
```python
apelido: str | None = None
nome_mae: str | None = None
foto_principal_url: str | None = None
```
Atualizar docstring idem.

**Step 4: Rodar testes**

Run: `pytest tests/unit/test_pessoa_schemas.py -v`
Expected: PASS (4 testes)

**Step 5: Commit**

```bash
git add app/schemas/pessoa.py tests/unit/test_pessoa_schemas.py
git commit -m "feat(pessoa): adicionar nome_mae aos schemas Pydantic"
```

---

## Task 3: Service — persistir `nome_mae` ao criar Pessoa

**Files:**
- Modify: `app/services/pessoa_service.py`
- Test: existente — adicionar caso em `tests/integration/test_pessoa_service.py` ou criar

**Step 1: Teste de integração**

Adicionar em `tests/integration/test_pessoa_service.py` (ou análogo existente):

```python
async def test_create_pessoa_persiste_nome_mae(db_session, guarnicao_fixture, user_fixture):
    from app.schemas.pessoa import PessoaCreate
    from app.services.pessoa_service import PessoaService

    svc = PessoaService(db_session)
    data = PessoaCreate(nome="Fulano da Silva", nome_mae="Maria da Silva")
    pessoa = await svc.create(
        data, guarnicao_id=guarnicao_fixture.id, user_id=user_fixture.id,
        ip_address="127.0.0.1", user_agent="pytest",
    )
    assert pessoa.nome_mae == "Maria da Silva"
```

**Step 2: Rodar e ver falhar**

Run: `pytest tests/integration/test_pessoa_service.py -k nome_mae -v`
Expected: FAIL (nome_mae não é propagado — é None)

**Step 3: Propagar campo no service**

Em [app/services/pessoa_service.py:90-98](app/services/pessoa_service.py#L90-L98):

```python
pessoa = Pessoa(
    nome=data.nome,
    cpf_encrypted=cpf_encrypted,
    cpf_hash=cpf_hash,
    data_nascimento=data.data_nascimento,
    apelido=data.apelido,
    nome_mae=data.nome_mae,
    observacoes=data.observacoes,
    guarnicao_id=guarnicao_id,
)
```

Verificar método `update` no mesmo arquivo e adicionar suporte a `nome_mae` se seguir padrão similar (se usar `model_dump(exclude_unset=True)` já funciona).

**Step 4: Rodar**

Run: `pytest tests/integration/test_pessoa_service.py -k nome_mae -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/pessoa_service.py tests/integration/test_pessoa_service.py
git commit -m "feat(pessoa): service persiste nome_mae ao criar pessoa"
```

---

## Task 4: Migration Alembic — adicionar coluna + índice GIN trgm

**Files:**
- Create: `alembic/versions/<nova_revision>_add_nome_mae_pessoa.py`

**Step 1: Gerar migration**

Run: `make migrate msg="add nome_mae em pessoa"`

Abrir o arquivo gerado.

**Step 2: Escrever upgrade/downgrade idempotentes**

Substituir o corpo gerado por (manter revision/down_revision que o Alembic preencheu):

```python
def upgrade() -> None:
    op.execute(
        "ALTER TABLE pessoas ADD COLUMN IF NOT EXISTS nome_mae VARCHAR(300)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pessoa_nome_mae_trgm "
        "ON pessoas USING gin (nome_mae gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pessoas_nome_mae ON pessoas (nome_mae)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pessoas_nome_mae")
    op.execute("DROP INDEX IF EXISTS idx_pessoa_nome_mae_trgm")
    op.execute("ALTER TABLE pessoas DROP COLUMN IF EXISTS nome_mae")
```

Referência do padrão idempotente: commit `f300170` (migrations anteriores do projeto).

**Step 3: Aplicar migration localmente**

Run: `docker compose exec api alembic upgrade head`
Expected: migration aplica sem erro. Se já rodou antes, `IF NOT EXISTS` garante idempotência.

**Step 4: Verificar coluna e índice no banco**

Run:
```bash
docker compose exec db psql -U argus -d argus -c "\d pessoas" | grep -i nome_mae
docker compose exec db psql -U argus -d argus -c "\di pessoas" | grep nome_mae
```
Expected: coluna `nome_mae varchar(300)` e índices `idx_pessoa_nome_mae_trgm` + `ix_pessoas_nome_mae` listados.

**Step 5: Testar downgrade → upgrade**

```bash
docker compose exec api alembic downgrade -1
docker compose exec api alembic upgrade head
```
Expected: ambos rodam sem erro.

**Step 6: Commit**

```bash
git add alembic/versions/<arquivo_gerado>.py
git commit -m "fix(migrations): adicionar nome_mae em pessoas com indice GIN trgm"
```

---

## Task 5: Frontend — `abordagem-nova.js` formulário Nova Pessoa

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js`
- Modify: `frontend/index.html` (cache buster)

**Step 1: Adicionar campo no template**

Em [frontend/js/pages/abordagem-nova.js:88-99](frontend/js/pages/abordagem-nova.js#L88-L99), após o grid com Data de Nascimento e Vulgo, antes do bloco de Endereço (linha 101), inserir:

```html
<div>
  <label class="login-field-label">Nome da mãe</label>
  <input type="text" x-model="novaPessoa.nome_mae" placeholder="Nome completo da mãe" maxlength="300">
</div>
```

**Step 2: Adicionar `nome_mae` em TODOS os resets do estado**

Procurar no arquivo todas as inicializações de `novaPessoa` e incluir `nome_mae:''`:

Linhas a modificar (conferir contexto de cada uma antes de editar):
- Linha 74: botão cancelar do modal
- Linha 518: estado inicial
- Linha 609 e 611: reset ao abrir para cadastro com CPF/nome pré-preenchido
- Linha 721: reset após cadastro bem-sucedido
- Linha 996: reset externo

Padrão antes → depois:
```js
// antes
novaPessoa = {nome:'',cpf:'',data_nascimento:'',apelido:'',endereco:''}
// depois
novaPessoa = {nome:'',cpf:'',data_nascimento:'',apelido:'',nome_mae:'',endereco:''}
```

**Step 3: Enviar `nome_mae` no POST**

Na função de submit (por volta da linha 694 onde trata `apelido`), adicionar logo após:

```js
if (this.novaPessoa.apelido.trim()) {
  pessoaData.apelido = this.novaPessoa.apelido.trim();
}
if (this.novaPessoa.nome_mae.trim()) {
  pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();
}
```

**Step 4: Bumpar cache buster**

Em [frontend/index.html:162](frontend/index.html#L162):
```html
<script src="/js/pages/abordagem-nova.js?v=12"></script>
```
(incrementar de `v=11` para `v=12`)

**Step 5: Teste manual**

1. `docker compose up -d`
2. Abrir http://localhost:8000/#/abordagem/nova
3. Adicionar pessoa não cadastrada
4. Preencher nome, data, vulgo, **nome da mãe**, endereço
5. Salvar e verificar no banco:
   ```bash
   docker compose exec db psql -U argus -d argus -c \
     "SELECT id, nome, apelido, nome_mae FROM pessoas ORDER BY id DESC LIMIT 1"
   ```
6. Testar com nome da mãe vazio → deve permitir (NULL no banco).

**Step 6: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js frontend/index.html
git commit -m "feat(abordagem): campo nome da mae no cadastro de pessoa nova"
```

---

## Task 6: Frontend — `consulta.js` formulário + exibição em cards

**Files:**
- Modify: `frontend/js/pages/consulta.js`
- Modify: `frontend/index.html` (cache buster)

**Step 1: Adicionar campo no formulário de cadastro**

Em [frontend/js/pages/consulta.js:214](frontend/js/pages/consulta.js#L214) (após o grid com Data de Nascimento/Vulgo, antes de Endereço):

```html
<div>
  <label class="login-field-label">Nome da mae</label>
  <input type="text" x-model="novaPessoa.nome_mae" placeholder="Nome completo da mae" maxlength="300">
</div>
```

Nota: manter acentuação consistente com o restante do arquivo (que usa sem acento em vários lugares).

**Step 2: Adicionar `nome_mae` em todos os resets**

Linhas: 26, 187, 678, 991.

Padrão antes → depois:
```js
novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', nome_mae: '', endereco: '' }
```

**Step 3: Enviar no POST**

Perto da linha 969:
```js
if (this.novaPessoa.apelido.trim()) pessoaData.apelido = this.novaPessoa.apelido.trim();
if (this.novaPessoa.nome_mae.trim()) pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();
```

**Step 4: Exibir em cards de resultado**

Nas linhas 110, 140, 380, 463 existe:
```html
<p x-show="p.apelido" style="..." x-text="'Vulgo: ' + p.apelido"></p>
```

Logo após cada ocorrência, adicionar:
```html
<p x-show="p.nome_mae" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Mae: ' + p.nome_mae"></p>
```

(variáveis `r.nome_mae` e `p.nome_mae` conforme o contexto de cada linha — verificar qual letra o bloco está usando).

**Step 5: Bumpar cache buster**

Em [frontend/index.html:163](frontend/index.html#L163):
```html
<script src="/js/pages/consulta.js?v=6"></script>
```
(de `v=5` para `v=6`)

**Step 6: Teste manual**

1. Abrir Consulta IA.
2. Cadastrar pessoa nova com nome da mãe preenchido.
3. Verificar no banco (query da Task 5).
4. Buscar pela pessoa cadastrada e confirmar que o card exibe "Mae: X".
5. Testar pessoa sem nome da mãe → card não exibe a linha (x-show oculta).

**Step 7: Commit**

```bash
git add frontend/js/pages/consulta.js frontend/index.html
git commit -m "feat(consulta): campo nome da mae no cadastro e exibicao em resultados"
```

---

## Task 7: Verificação final

**Step 1: Rodar suite completa de testes**

Run: `make test`
Expected: todos os testes passam.

**Step 2: Lint + type check**

Run: `make lint`
Expected: sem erros ruff/mypy.

**Step 3: Sanity check dos endpoints**

```bash
# criar pessoa com nome_mae via API
curl -X POST http://localhost:8000/api/v1/pessoas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nome":"Teste Mae","nome_mae":"Maria Teste"}'

# ler de volta
curl http://localhost:8000/api/v1/pessoas/<id> -H "Authorization: Bearer $TOKEN" | jq .nome_mae
```
Expected: `"Maria Teste"` no GET.

**Step 4: Confirmar índice GIN funcional**

```bash
docker compose exec db psql -U argus -d argus -c \
  "EXPLAIN SELECT * FROM pessoas WHERE nome_mae % 'maria'"
```
Expected: plano usa `idx_pessoa_nome_mae_trgm`.

---

## Checklist final

- [ ] Model tem `nome_mae` + índice GIN
- [ ] Schemas Create/Update/Read têm `nome_mae`
- [ ] Service persiste `nome_mae`
- [ ] Migration idempotente aplicada e revertível
- [ ] `abordagem-nova.js` — input, resets, POST, cache buster
- [ ] `consulta.js` — input, resets, POST, exibição em cards, cache buster
- [ ] `make test` verde
- [ ] `make lint` limpo
- [ ] Teste manual end-to-end nos dois formulários
- [ ] Card de consulta mostra "Mae: X" quando preenchido
