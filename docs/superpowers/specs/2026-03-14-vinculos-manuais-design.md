# Vínculos Manuais entre Pessoas — Design Spec

**Data:** 2026-03-14
**Status:** Aprovado pelo usuário

---

## Contexto

A página de detalhe de pessoa (`pessoa-detalhe.js`) exibe um container de "Vínculos" que mostra pessoas abordadas juntas com frequência e data da última abordagem conjunta. Esse dado é gerado automaticamente pelo sistema durante o cadastro de abordagens.

O objetivo desta feature é permitir que o operador cadastre **vínculos manuais** — relações conhecidas operacionalmente mas que não têm registro formal em abordagens (ex: "Irmão", "Sócio", "Traficando junto na casa ao lado").

---

## O que será construído

### 1. Banco de dados — nova tabela `vinculos_manuais`

Nova tabela independente da `relacionamento_pessoas` existente. A tabela atual tem constraints incompatíveis com vínculos manuais (`frequencia`, `primeira_abordagem_id NOT NULL`, `CHECK pessoa_id_a < pessoa_id_b`).

**Model `VinculoManual`** herda `Base`, `TimestampMixin`, `SoftDeleteMixin`, `MultiTenantMixin`.

> `MultiTenantMixin` já declara `guarnicao_id` como FK → `guarnicoes.id`. Não redeclarar no modelo.
> `SoftDeleteMixin` declara `ativo: bool = True`, `desativado_em: datetime|None`, `desativado_por_id: int|None`.

**Campos adicionais:**

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `pessoa_id` | FK → pessoas (CASCADE) | Pessoa sendo visualizada |
| `pessoa_vinculada_id` | FK → pessoas (CASCADE) | Pessoa vinculada |
| `tipo` | String(100) | Obrigatório — ex: "Irmão", "Sócio" |
| `descricao` | String(500) | Opcional — ex: "Traficando junto na casa ao lado" |

**Constraints:**
- `UNIQUE(pessoa_id, pessoa_vinculada_id)` — evita duplicatas
- `CHECK(pessoa_id != pessoa_vinculada_id)` — pessoa não pode se vincular a si mesma

> **Nota:** Vínculos não são bidirecionais — `(A→B)` e `(B→A)` são registros distintos e ambos são permitidos. Isso é intencional e diferente de `RelacionamentoPessoa` que força `pessoa_id_a < pessoa_id_b`.

**Índices:** `pessoa_id`, `pessoa_vinculada_id` (além dos herdados de `MultiTenantMixin`)

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
POST   /pessoas/{pessoa_id}/vinculos-manuais   @limiter.limit("30/minute")
DELETE /pessoas/{pessoa_id}/vinculos-manuais/{vinculo_id}
```

Ambos delegam inteiramente ao `PessoaService` — **nenhuma lógica no router**.

**POST** → `VinculoManualRead` com status 201
**DELETE** → 204

**GET /pessoas/{pessoa_id}** — `detalhe_pessoa` atualizado:
- Chama `service.buscar_detalhe()` que retorna `PessoaDetail` completo
- O router apenas serializa o retorno — toda a montagem (incluindo vínculos manuais) fica no service
- O helper `_to_pessoa_read()` permanece no router apenas para os endpoints de listagem

---

### 4. Service — métodos em `PessoaService`

> `app.core.exceptions` é importável em services — padrão já estabelecido em `abordagem_service.py`.

**`criar_vinculo_manual(pessoa_id, data, user, ip_address, user_agent)`:**
1. Verifica que `pessoa_id` pertence à guarnição do user (TenantFilter)
2. Verifica que `pessoa_vinculada_id` pertence à **mesma** guarnição → `AcessoNegadoError` se não (proteção cross-tenant)
3. Tenta criar `VinculoManual` com `guarnicao_id = user.guarnicao_id`
4. Captura `IntegrityError` do banco (race condition na constraint UNIQUE) → relança como `ConflitoDadosError`
5. Registra `AuditLog`: ação `CREATE`, entidade `vinculo_manual`
6. Retorna `VinculoManual`

**`listar_vinculos_manuais(pessoa_id, user)` *(somente leitura — sem ip_address/user_agent)*:**
- Filtra por `pessoa_id` + `guarnicao_id = user.guarnicao_id` + `ativo == True`
- Retorna `list[VinculoManual]`

**`remover_vinculo_manual(vinculo_id, pessoa_id, user, ip_address, user_agent)`:**
1. Busca vínculo por `vinculo_id` + `pessoa_id`, valida guarnição → `NaoEncontradoError` se não encontrado
2. Soft delete: `ativo = False`, `desativado_em = now()`, `desativado_por_id = user.id`
3. Registra `AuditLog`: ação `DELETE`, entidade `vinculo_manual`

**`buscar_detalhe()` atualizado:**
- Carrega `vinculos_manuais` da pessoa (query: `pessoa_id`, `guarnicao_id`, `ativo == True`)
- Monta lista de `VinculoManualRead` com nome e `foto_principal_url` da pessoa vinculada
- Retorna `PessoaDetail` completo — toda a montagem acontece no service, não no router

---

### 5. Migration Alembic

Nova migration criando a tabela `vinculos_manuais` com todos os campos, constraints e índices.

---

### 6. Frontend — `pessoa-detalhe.js`

#### Estado Alpine.js adicionado

```js
vinculosManuais: [],
modalVinculo: false,
buscaVinculo: '',
resultadosBusca: [],
buscandoPessoa: false,
pessoaSelecionada: null,
novoVinculo: { tipo: '', descricao: '' },
subFormNovaPessoa: false,       // inicia false; true quando pessoa não encontrada
novaPessoaForm: { nome: '', cpf: '', apelido: '', data_nascimento: '' },
```

#### Container de vínculos — reestruturado

Um único card, sempre visível. Duas seções independentes com `x-show`:

```
┌─────────────────────────────────────────────────┐
│ Vínculos                          [+ Adicionar] │
├─────────────────────────────────────────────────┤
│ VÍNCULOS EM ABORDAGEM (N)    [x-show se N > 0]  │
│  [foto] João Silva          3x juntos           │
│  [foto] Maria Costa         1x juntos           │
├── separador (x-show se ambas as seções têm itens)┤
│ VÍNCULOS MANUAIS (N)         [x-show se N > 0]  │
│  [foto] Carlos Souza                            │
│         Irmão                    [roxo bold]    │
│         "Traficando junto..."    [itálico]      │
└─────────────────────────────────────────────────┘
```

- Vínculos manuais: borda esquerda `border-l-purple-500`
- Tipo: `text-purple-400 font-semibold`
- Descrição: `text-slate-400 text-xs italic` — só exibida se preenchida
- Clicar em qualquer vínculo abre a ficha da pessoa (`viewPessoa(id)`)
- `vinculosManuais` é carregado de `pessoa.vinculos_manuais` no `load()` (vem no `GET /pessoas/{id}`)

#### Modal de cadastro de vínculo manual

**Fluxo:**
1. Usuário digita nome → debounce 400ms → `GET /pessoas?nome=...&limit=5`
2. Seleciona pessoa da lista → `pessoaSelecionada` preenchida, dropdown fecha
3. **Se não encontrar:** exibe opção "Cadastrar [nome digitado]" → clique → `subFormNovaPessoa = true`
   - Campos: `nome` (pré-preenchido com o texto digitado, obrigatório), `cpf` (opcional), `apelido` (opcional), `data_nascimento` (opcional)
   - Clique em "Cadastrar" → `POST /pessoas/` → pessoa retornada vira `pessoaSelecionada` → `subFormNovaPessoa = false`
4. Preenche `tipo` (obrigatório) + `descricao` (opcional)
5. Clique em "Salvar Vínculo" → `POST /pessoas/{id}/vinculos-manuais`
6. Resposta adicionada ao início de `vinculosManuais` → modal fecha → estado do modal resetado

---

## O que não muda

- Lógica de `RelacionamentoPessoa` (vínculos automáticos via abordagem) — zero alterações
- Endpoint `GET /pessoas/{id}/abordagens` — sem alterações
- Demais seções da ficha de pessoa — sem alterações

---

## Fora de escopo (pode vir depois)

- Editar um vínculo manual existente
- Exibir vínculo manual na ficha da *outra* pessoa também (bidirecionalidade automática)
- Filtrar/buscar pessoas por vínculo manual
