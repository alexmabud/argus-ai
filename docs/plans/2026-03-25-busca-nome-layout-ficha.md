# Busca por Nome + Layout da Ficha — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir busca por primeiro nome (com suporte a acentos/case) e reposicionar "Cadastrado em" na ficha.

**Architecture:** Substituir `pg_trgm similarity()` por `unaccent + ILIKE` com ordenação por posição do match no nome. Ajustar layout HTML dos containers de endereço e histórico na ficha.

**Tech Stack:** PostgreSQL (unaccent extension), SQLAlchemy async, Alpine.js frontend

---

### Task 1: Migration — Extensão unaccent

**Files:**
- Create: `alembic/versions/f1a2b3c4d5e6_add_unaccent_extension.py`

**Step 1: Criar migration Alembic**

```bash
cd c:/projetos/argus_ai && alembic revision --autogenerate -m "add_unaccent_extension"
```

Editar o arquivo gerado para conter:

```python
"""add_unaccent_extension

Revision ID: <auto>
"""
from alembic import op


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS unaccent")
```

**Step 2: Aplicar migration (verificar localmente)**

```bash
alembic upgrade head
```

Expected: Migration aplicada com sucesso.

**Step 3: Commit**

```bash
git add alembic/versions/*unaccent*
git commit -m "feat(db): adicionar extensão unaccent para busca sem acentos"
```

---

### Task 2: Novo método de busca no repositório

**Files:**
- Modify: `app/repositories/pessoa_repo.py:41-73`

**Step 1: Adicionar método `search_by_nome_contains` em `PessoaRepository`**

Adicionar após o método `search_by_nome_fuzzy` (que permanece no código para uso futuro):

```python
async def search_by_nome_contains(
    self,
    nome: str,
    guarnicao_id: int | None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Pessoa]:
    """Busca pessoas por substring no nome, ignorando acentos e case.

    Utiliza unaccent + ILIKE para busca parcial. Resultados são
    ordenados pela posição do match no nome (primeiro nome = prioridade maior).

    Args:
        nome: Termo de busca (nome ou parte do nome).
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        skip: Número de registros a pular.
        limit: Número máximo de resultados.

    Returns:
        Sequência de Pessoas ordenadas por posição do match no nome.
    """
    nome_clean = nome.strip()
    if not nome_clean:
        return []

    unaccent_nome = func.unaccent(func.lower(Pessoa.nome))
    unaccent_query = func.unaccent(func.lower(nome_clean))

    query = select(Pessoa).where(
        Pessoa.ativo == True,  # noqa: E712
        unaccent_nome.like("%" + unaccent_query + "%"),
    )
    if guarnicao_id is not None:
        query = query.where(Pessoa.guarnicao_id == guarnicao_id)

    query = (
        query.order_by(
            func.position(unaccent_query, unaccent_nome).asc()
        )
        .offset(skip)
        .limit(limit)
    )
    result = await self.db.execute(query)
    return result.scalars().all()
```

**Nota importante:** A concatenação `"%" + unaccent_query + "%"` no SQLAlchemy gera SQL parametrizado seguro (`LIKE '%' || $1 || '%'`), não string interpolation.

**Step 2: Verificar que o arquivo salvo não tem erros de sintaxe**

```bash
python -c "import ast; ast.parse(open('app/repositories/pessoa_repo.py').read()); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add app/repositories/pessoa_repo.py
git commit -m "feat(repo): adicionar search_by_nome_contains com unaccent + ILIKE"
```

---

### Task 3: Trocar chamada no service

**Files:**
- Modify: `app/services/consulta_service.py:214-217`

**Step 1: Alterar `_buscar_pessoas` para usar `search_by_nome_contains`**

Em `app/services/consulta_service.py`, linhas 214-217, substituir:

```python
# Antes
fuzzy_results = await self.pessoa_repo.search_by_nome_fuzzy(
    q, guarnicao_id, skip=skip, limit=limit
)
```

Por:

```python
# Depois
fuzzy_results = await self.pessoa_repo.search_by_nome_contains(
    q, guarnicao_id, skip=skip, limit=limit
)
```

**Step 2: Verificar sintaxe**

```bash
python -c "import ast; ast.parse(open('app/services/consulta_service.py').read()); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add app/services/consulta_service.py
git commit -m "feat(service): usar search_by_nome_contains na busca unificada"
```

---

### Task 4: Remover filtro client-side no frontend

**Files:**
- Modify: `frontend/js/pages/consulta.js:558-576`

**Step 1: Simplificar `searchPorTexto` — remover `.filter()` client-side**

Substituir o bloco em `consulta.js` linhas 558-576:

```javascript
// Antes
async searchPorTexto() {
  this.loadingPessoa = true;
  this.buscouPessoa = true;
  try {
    const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`;
    const r = await api.get(url);
    const q = this.query.toLowerCase();
    this.pessoasTexto = (r.pessoas || []).filter(p =>
      (p.nome || "").toLowerCase().includes(q) ||
      (p.apelido || "").toLowerCase().includes(q) ||
      (p.cpf_masked || "").includes(q)
    );
    this.searched = true;
  } catch {
    showToast("Erro na busca por nome/CPF", "error");
  } finally {
    this.loadingPessoa = false;
  }
},
```

Por:

```javascript
// Depois
async searchPorTexto() {
  this.loadingPessoa = true;
  this.buscouPessoa = true;
  try {
    const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`;
    const r = await api.get(url);
    this.pessoasTexto = r.pessoas || [];
    this.searched = true;
  } catch {
    showToast("Erro na busca por nome/CPF", "error");
  } finally {
    this.loadingPessoa = false;
  }
},
```

**Step 2: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "fix(frontend): remover filtro client-side redundante na busca por nome"
```

---

### Task 5: Layout — Reposicionar "Cadastrado em" nos endereços

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:435-450`

**Step 1: Reestruturar layout dos endereços**

Substituir linhas 435-450 (o conteúdo interno de cada card de endereço):

```html
<!-- Antes -->
<div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
  <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem;">
    <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0; flex: 1;" x-text="formatEndereco(end)"></p>
    <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
      <button @click="abrirModalEditarEndereco(end)" ...>...</button>
      <span x-show="end.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
            x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
    </div>
  </div>
```

Por:

```html
<!-- Depois -->
<div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
  <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem; margin-bottom: 0.375rem;">
    <span x-show="end.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
          x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
    <button @click="abrirModalEditarEndereco(end)"
            style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); padding: 0.125rem; transition: color 0.15s;"
            onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
            title="Editar endereço">
      <svg style="width: 0.75rem; height: 0.75rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/>
      </svg>
    </button>
  </div>
  <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0;" x-text="formatEndereco(end)"></p>
```

**Mudança:** A data + botão de editar vão para uma `div` própria acima (alinhada à direita), e o endereço fica em `<p>` abaixo com largura total.

**Step 2: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): mover data de cadastro para linha acima nos endereços da ficha"
```

---

### Task 6: Layout — Reposicionar "Cadastrada em" no histórico de abordagens

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:608-615`

**Step 1: Reestruturar layout do histórico**

Substituir linhas 608-615:

```html
<!-- Antes -->
<div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;">
  <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem;">
    <div>
      <span style="font-size: 0.75rem; font-weight: 500; color: var(--color-primary);" x-text="'#' + ab.id"></span>
    </div>
    <span x-show="ab.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim); flex-shrink: 0;"
          x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
  </div>
```

Por:

```html
<!-- Depois -->
<div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;">
  <div style="display: flex; align-items: center; justify-content: flex-end;">
    <span x-show="ab.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
          x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
  </div>
  <div>
    <span style="font-size: 0.75rem; font-weight: 500; color: var(--color-primary);" x-text="'#' + ab.id"></span>
  </div>
```

**Mudança:** A data sobe para linha própria (alinhada à direita). O `#id` da abordagem fica na linha abaixo, seguido do resto do conteúdo (endereço, observação, veículos, coabordados).

**Step 2: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): mover data de cadastro para linha acima no histórico de abordagens"
```

---

### Task 7: Teste manual end-to-end

**Step 1: Subir o ambiente**

```bash
cd c:/projetos/argus_ai && docker compose up -d --build
```

**Step 2: Testar busca por primeiro nome**

1. Abrir `http://localhost:8000` > Consulta
2. Digitar apenas o primeiro nome de uma pessoa cadastrada (ex: "João")
3. Verificar que resultados aparecem ordenados: quem tem "João" como primeiro nome primeiro
4. Digitar "joao" (sem acento, minúscula) — deve retornar os mesmos resultados
5. Digitar "JOÃO" — deve retornar os mesmos resultados

**Step 3: Testar layout da ficha**

1. Clicar em uma pessoa com endereços cadastrados
2. Verificar que "Cadastrado em DD/MM/AAAA" aparece na linha acima do endereço, alinhado à direita
3. Verificar que o botão de editar está ao lado da data
4. Rolar até Histórico de Abordagens
5. Verificar que "Cadastrada em DD/MM/AAAA às HH:MM" aparece na linha acima do conteúdo da abordagem

**Step 4: Commit final (se houve ajuste)**

```bash
git add -A && git commit -m "fix: ajustes finais busca por nome e layout ficha"
```
