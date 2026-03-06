# Design: Melhorias na Consulta em Campo

**Data:** 2026-03-06
**Escopo:** `frontend/js/pages/pessoa-detalhe.js`, `frontend/js/pages/consulta.js`, `app/repositories/pessoa_repo.py`, `app/api/v1/consultas.py`, `app/schemas/consulta.py`

## Objetivo

Melhorar a usabilidade da consulta em campo com três ajustes:

1. Reordenar campos de "Dados Pessoais" em pessoa-detalhe
2. Exibir data de cadastro do endereço nos resultados de busca por endereço
3. Exibir data de cadastro do veículo nos resultados de busca por veículo

---

## Mudança 1 — Reordenar "Dados Pessoais" (`pessoa-detalhe.js`)

**Arquivo:** `frontend/js/pages/pessoa-detalhe.js` (linhas 34–50)

**Atual:**
```
CPF         | Nascimento
Abordagens  | Cadastro
```

**Novo:**
```
CPF         | Nascimento
Cadastro    | Abordagens
```

Apenas troca as divs de "Abordagens" e "Cadastro" dentro da grade 2×2. Mudança puramente frontend, sem impacto em API.

---

## Mudança 2 — Data de cadastro do endereço nos resultados (`consulta.js` + backend)

**Contexto:** A busca por endereço retorna objetos `PessoaRead`, que não contêm dados do endereço que gerou o match.

**Solução:**

### Backend

1. **`app/repositories/pessoa_repo.py`** — Novo método `search_by_bairro_cidade_com_endereco` que faz SELECT de `(Pessoa, EnderecoPessoa.criado_em)` retornando tuplas com a data de cadastro do endereço correspondente.

2. **`app/schemas/consulta.py`** — Novo schema `PessoaComEnderecoRead(PessoaRead)` com campo adicional:
   ```python
   endereco_criado_em: datetime | None = None
   ```

3. **`app/api/v1/consultas.py`** — No endpoint `consulta_unificada`, quando busca por endereço (filtro_local ativo), usar `PessoaComEnderecoRead` em vez de `PessoaRead` para mapear as pessoas. Atualizar `ConsultaUnificadaResponse` para aceitar `list[PessoaComEnderecoRead]`.

### Frontend

4. **`frontend/js/pages/consulta.js`** — No card de resultado de pessoa por endereço, adicionar linha:
   ```
   Endereço cadastrado em DD/MM/AAAA
   ```
   Usando `p.endereco_criado_em` com `new Date(...).toLocaleDateString('pt-BR')`.

---

## Mudança 3 — Data de cadastro do veículo nos resultados (`consulta.js`)

**Contexto:** `VeiculoRead` já retorna `criado_em` — apenas exibição ausente no frontend.

**Arquivo:** `frontend/js/pages/consulta.js` (linhas 154–168)

Adicionar no card de veículo, abaixo da linha modelo/cor/ano:
```
Cadastrado em DD/MM/AAAA
```
Usando `v.criado_em` com `new Date(...).toLocaleDateString('pt-BR')`.

---

## Impacto

| Camada | Arquivo | Tipo |
|--------|---------|------|
| Frontend | `pessoa-detalhe.js` | Reordenação de HTML |
| Frontend | `consulta.js` | Exibição de campo existente (veículo) |
| Frontend | `consulta.js` | Exibição de novo campo (endereço) |
| Schema | `app/schemas/consulta.py` | Novo schema `PessoaComEnderecoRead` |
| Repositório | `app/repositories/pessoa_repo.py` | Novo método com join + criado_em |
| Router | `app/api/v1/consultas.py` | Usar novo método e schema |

## Sem impacto em

- Migrations (sem alteração de modelos)
- Testes de integração existentes (novo método adicional, não modifica o atual)
- Autenticação, multi-tenancy, soft delete
