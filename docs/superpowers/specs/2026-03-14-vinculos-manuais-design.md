# Vínculos Manuais entre Pessoas — Design Spec

**Data:** 2026-03-14
**Status:** Aprovado pelo usuário

---

## Contexto

A página de detalhe de pessoa (`pessoa-detalhe.js`) exibe um container de "Vínculos" que mostra pessoas abordadas juntas com frequência e data da última abordagem conjunta. Esse dado é gerado automaticamente pelo sistema durante o cadastro de abordagens.

O objetivo desta feature é permitir que o operador cadastre **vínculos manuais** — relações conhecidas operacionalmente mas que não têm registro formal em abordagens (ex: "Irmão", "Sócio", "Traficando junto na casa ao lado").

---

## O que será construído

### 1. Banco de dados — nova tabela `vinculo_manuais`

Nova tabela independente da `relacionamento_pessoas` existente. A tabela atual tem constraints incompatíveis com vínculos manuais (`frequencia`, `primeira_abordagem_id NOT NULL`, `CHECK pessoa_id_a < pessoa_id_b`).

**Campos:**

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `pessoa_id` | FK → pessoas (CASCADE) | Pessoa sendo visualizada |
| `pessoa_vinculada_id` | FK → pessoas (CASCADE) | Pessoa vinculada |
| `tipo` | String(100) | Obrigatório — ex: "Irmão", "Sócio" |
| `descricao` | String(500) | Opcional — ex: "Traficando junto na casa ao lado" |
| `guarnicao_id` | FK → guarnicoes | Multi-tenancy |
| `criado_em` | DateTime | TimestampMixin |
| `atualizado_em` | DateTime | TimestampMixin |
| `deletado_em` | DateTime | SoftDeleteMixin |

**Constraints:**
- `UNIQUE(pessoa_id, pessoa_vinculada_id)` — evita duplicatas
- `CHECK(pessoa_id != pessoa_vinculada_id)` — pessoa não pode se vincular a si mesma

**Índices:** `pessoa_id`, `pessoa_vinculada_id`, `guarnicao_id`

---

### 2. Schemas Pydantic

**`VinculoManualCreate`:**
- `pessoa_vinculada_id: int` — obrigatório
- `tipo: str` — obrigatório, 1–100 chars
- `descricao: str | None` — opcional, máx 500 chars

**`VinculoManualRead`:**
- `id: int`
- `pessoa_vinculada_id: int`
- `nome: str` — nome da pessoa vinculada
- `foto_principal_url: str | None`
- `tipo: str`
- `descricao: str | None`
- `criado_em: datetime`

**`PessoaDetail`** recebe campo adicional:
- `vinculos_manuais: list[VinculoManualRead] = []`

---

### 3. Endpoints novos em `/pessoas`

```
POST   /pessoas/{pessoa_id}/vinculos-manuais
DELETE /pessoas/{pessoa_id}/vinculos-manuais/{vinculo_id}
```

**POST** — cria vínculo manual
- Body: `VinculoManualCreate`
- Valida que `pessoa_id` e `pessoa_vinculada_id` pertencem à mesma guarnição
- Retorna `VinculoManualRead` com status 201
- Lança `ConflitoDadosError` se vínculo já existe

**DELETE** — soft delete do vínculo
- Retorna 204
- Lança `NaoEncontradoError` se não encontrado ou de outra guarnição

**GET /pessoas/{pessoa_id}** — retorna `PessoaDetail` já existente, agora inclui `vinculos_manuais`

---

### 4. Service — métodos em `PessoaService`

- `criar_vinculo_manual(pessoa_id, data, user) → VinculoManual`
- `listar_vinculos_manuais(pessoa_id, guarnicao_id) → list[VinculoManual]`
- `remover_vinculo_manual(vinculo_id, pessoa_id, user) → None`

`buscar_detalhe()` é atualizado para carregar `vinculos_manuais` junto com a pessoa.

---

### 5. Migration Alembic

Nova migration criando a tabela `vinculo_manuais` com todos os campos, constraints e índices.

---

### 6. Frontend — `pessoa-detalhe.js`

#### Estado Alpine.js adicionado

```js
vinculosManuais: [],        // lista de vínculos manuais
modalVinculo: false,        // controla abertura do modal
buscaVinculo: '',           // texto de busca de pessoa
resultadosBusca: [],        // resultados do GET /pessoas?nome=...
buscandoPessoa: false,      // loading da busca
pessoaSelecionada: null,    // pessoa escolhida para vincular
novoVinculo: { tipo: '', descricao: '' },
subFormNovaPessoa: false,   // true quando pessoa não encontrada → form de cadastro
```

#### Container de vínculos — reestruturado

O card atual "Vínculos" é dividido em duas seções dentro de um único card:

```
┌─────────────────────────────────────────────────┐
│ Vínculos                          [+ Adicionar] │
├─────────────────────────────────────────────────┤
│ VÍNCULOS EM ABORDAGEM (N)                       │
│  [foto] João Silva          3x juntos           │
│  [foto] Maria Costa         1x juntos           │
├── separador ────────────────────────────────────┤
│ VÍNCULOS MANUAIS (N)                            │
│  [foto] Carlos Souza                            │
│         Irmão                                   │
│         "Traficando junto na casa ao lado"      │
└─────────────────────────────────────────────────┘
```

- Card sempre visível (para o botão "+ Adicionar" estar acessível)
- Seção "Abordagem" só aparece se `pessoa.relacionamentos?.length > 0`
- Seção "Manuais" só aparece se `vinculosManuais.length > 0`
- Vínculos manuais: borda roxa (`border-l-purple-500`), tipo em `text-purple-400`, descrição em itálico abaixo
- Clicar em qualquer vínculo (abordagem ou manual) abre a ficha da pessoa

#### Modal de cadastro de vínculo manual

**Fluxo:**
1. Usuário digita nome → debounce 400ms → `GET /pessoas?nome=...&limit=5`
2. Seleciona pessoa da lista → `pessoaSelecionada` preenchida
3. Se não encontrar → botão "Cadastrar [nome digitado]" → `subFormNovaPessoa = true` → exibe campos nome/CPF/apelido/nascimento inline → `POST /pessoas/` → pessoa retornada vira `pessoaSelecionada`
4. Preenche `tipo` (obrigatório) + `descricao` (opcional)
5. Salvar → `POST /pessoas/{id}/vinculos-manuais` → adiciona à lista `vinculosManuais` → fecha modal

---

## O que não muda

- Lógica de `RelacionamentoPessoa` (vínculos automáticos via abordagem) — zero alterações
- Endpoint `GET /pessoas/{id}/abordagens` — sem alterações
- Demais seções da ficha de pessoa — sem alterações

---

## Fora de escopo (pode vir depois)

- Editar um vínculo manual existente
- Exibir vínculo manual na ficha da *outra* pessoa também (bidirecionalidade)
- Filtrar/buscar pessoas por vínculo manual
