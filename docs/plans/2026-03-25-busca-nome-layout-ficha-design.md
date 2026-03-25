# Design: Busca por nome + Layout da ficha

**Data:** 2026-03-25
**Status:** Aprovado

## Problema

1. **Busca por primeiro nome não funciona** — o `pg_trgm similarity()` compara a string inteira, então digitar apenas o primeiro nome gera score baixo e não retorna resultados
2. **Case e acentos não são ignorados** — buscar "joao" não encontra "João"
3. **Layout da ficha** — nos containers de endereço e histórico de abordagens, o campo "Cadastrado em" disputa espaço horizontal com o conteúdo principal

## Solução

### 1. Busca por nome: `unaccent + ILIKE` com ordenação por posição

**Migration Alembic:**
- Criar extensão `unaccent` no PostgreSQL

**Repository (`pessoa_repo.py`):**
- Novo método `search_by_nome_contains`
- Query: `WHERE unaccent(lower(nome)) LIKE '%' || unaccent(lower(:query)) || '%'`
- Ordenação: `position(unaccent(lower(:query)) in unaccent(lower(nome)))` ASC
  - Match no primeiro nome = posição menor = aparece primeiro
  - Match no segundo nome = posição maior = aparece depois
- Manter filtros `ativo == True` e `guarnicao_id`

**Service (`consulta_service.py`):**
- Trocar chamada de `search_by_nome_fuzzy` por `search_by_nome_contains`

**Frontend (`consulta.js`):**
- Remover filtro `.filter()` client-side com `.includes(q)` — backend já retorna resultados corretos e ordenados

### 2. Case + acentos

Coberto automaticamente pela Opção A:
- `unaccent()` normaliza acentos (João → Joao)
- `lower()` normaliza case (JOÃO → joão)

### 3. Layout da ficha

**Endereços (`pessoa-detalhe.js`):**
```
Antes:
  flex-row: [endereço texto] ←→ [botão editar + "Cadastrado em ..."]

Depois:
  linha 1 (flex-row, justify-end): "Cadastrado em 01/01/2026"  [botão editar]
  linha 2: endereço texto (largura total)
```

**Histórico de abordagens (`pessoa-detalhe.js`):**
```
Antes:
  flex-row: [info abordagem] ←→ ["Cadastrada em ..."]

Depois:
  linha 1 (flex-row, justify-end): "Cadastrada em 01/01/2026 às 14:30"
  linha 2: informações da abordagem (largura total)
```

Estilo mantido: `font-size: 0.75rem`, `color: var(--color-text-dim)`.

## Arquivos impactados

| Arquivo | Mudança |
|---------|---------|
| Nova migration Alembic | `CREATE EXTENSION IF NOT EXISTS unaccent` |
| `app/repositories/pessoa_repo.py` | Novo método `search_by_nome_contains` |
| `app/services/consulta_service.py` | Trocar chamada para novo método |
| `frontend/js/pages/consulta.js` | Remover filtro client-side |
| `frontend/js/pages/pessoa-detalhe.js` | Reposicionar "cadastrado" nos containers |
