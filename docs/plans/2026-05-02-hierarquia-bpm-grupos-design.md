# Design: Hierarquia BPM > Grupo em Gerenciar Usuários

**Data:** 2026-05-02  
**Status:** Aprovado

## Contexto

A página de Gerenciar Usuários exibe abas planas por equipe (Guarnicao). Para suportar expansão do sistema a múltiplos batalhões, é necessário criar uma entidade BPM como nível hierárquico acima das equipes.

**Estado atual:**
- `Guarnicao` tem campo `unidade` (texto livre, ex: `"14º BPM"`, `"PMDF"`)
- Frontend: abas planas por guarnicão + aba global "Sem Equipe"

**Estado desejado:**
- BPM é uma entidade gerenciável no banco
- Navegação em 2 níveis: BPMs no topo → equipes dentro de cada BPM
- "Sem Equipe" global permanece (usuários sem guarnicao_id)

## Decisões

| Decisão | Escolha | Motivo |
|---|---|---|
| BPM como entidade | Nova tabela `bpm` | Gerenciável, escalável, hierarquia limpa |
| Campo `unidade` | Removido, substituído por `bpm_id` FK | BPM já representa a unidade |
| "Sem Equipe" | Global, fora de qualquer BPM | Centraliza usuários sem atribuição |
| BPM fields | Apenas `nome` | YAGNI — sem necessidade de campos extras |
| PMDF | BPM de primeiro nível (igual ao 14º BPM) | Não é grupo dentro de outro BPM |

## Modelo de Dados

### Nova tabela `bpm`

```
bpm
├── id          INT PK
├── nome        STRING(200) UNIQUE NOT NULL   ex: "14º BPM", "PMDF"
├── ativo       BOOL DEFAULT TRUE
├── criado_em   TIMESTAMP
└── atualizado_em TIMESTAMP
```

Herda `TimestampMixin` e `SoftDeleteMixin`.

### Tabela `guarnicoes` — alterações

```
REMOVE: unidade  STRING(200)
ADD:    bpm_id   INT FK → bpm.id  NOT NULL
```

Relacionamento: `Bpm (1) → (N) Guarnicao`

## Migration

Sequência segura para zero perda de dados:

1. Criar tabela `bpm`
2. Inserir `"14º BPM"` e `"PMDF"` em `bpm`
3. Adicionar coluna `bpm_id` em `guarnicoes` como nullable
4. `UPDATE guarnicoes SET bpm_id = bpm.id FROM bpm WHERE bpm.nome = guarnicoes.unidade`
5. Remover coluna `unidade`
6. Alterar `bpm_id` para NOT NULL

> Os valores atuais de `unidade` (`"14º BPM"` e `"PMDF"`) correspondem exatamente aos BPMs a serem criados.

## Backend

### Novo model `Bpm` (`app/models/bpm.py`)
- Campos: `id`, `nome`, `ativo`, mixins Timestamp + SoftDelete
- Relacionamento: `guarnicoes` (back_populates="bpm")

### Novo `BpmService` (`app/services/bpm_service.py`)
- `listar_bpms()` → lista BPMs ativos ordenados por nome
- `criar_bpm(nome, admin_id)` → cria BPM + audit log
- `desativar_bpm(bpm_id, admin_id)` → soft delete + audit log

### Novos schemas (`app/schemas/bpm.py`)
- `BpmRead`: `id`, `nome`
- `BpmCreate`: `nome`

### Novos endpoints (`app/api/v1/admin.py`)
- `GET /admin/bpms` → lista BPMs
- `POST /admin/bpms` → cria BPM

### Schemas atualizados
- `EquipeCreate`: troca `unidade: str` por `bpm_id: int`
- `EquipeRead`: troca `unidade: str` por `bpm_id: int` + `bpm_nome: str`

### Services atualizados
- `EquipeService.criar_equipe(nome, bpm_id, admin_id)` — remove parâmetro `unidade`
- `EquipeService.listar_equipes(bpm_id: int | None)` — filtro opcional por BPM

## Frontend

### Navegação em 2 níveis

```
[ 14º BPM ]  [ PMDF ]  [ Sem Equipe ]  [ + Novo BPM ]
      ↓ (BPM selecionado)
[ GU-01 ]  [ GU-02 ]  [ + Nova Equipe ]
      ↓ (equipe selecionada)
[ lista de usuários da equipe ]
```

### Comportamento

- **Aba BPM:** clica → carrega equipes daquele BPM, seleciona primeira aba automaticamente
- **Aba "Sem Equipe":** global, comportamento idêntico ao atual (usuários com `guarnicao_id = null`)
- **Aba "+ Novo BPM":** abre modal com campo `nome` → POST /admin/bpms
- **Aba "+ Nova Equipe":** visível dentro de um BPM ativo → formulário pede apenas `nome`; `bpm_id` vem da aba BPM ativa
- **Criar usuário:** seletor de equipe filtrado pelas equipes do BPM ativo (ou todas, se "Sem Equipe" for o contexto)

### Estado Alpine.js (`adminUsuariosPage`)

Adições ao estado atual:
```javascript
bpms: [],           // lista de BPMs carregados
bpmAtivo: null,     // id do BPM selecionado (null = "Sem Equipe")
equipesDosBpms: {}, // { [bpm_id]: [equipes] } — agrupado
novoBpm: { nome: "" },
```

### Carregamento

`carregar()` passa a chamar também `GET /admin/bpms` em paralelo com os demais endpoints existentes.

## Fora do escopo

- Renomear ou excluir BPMs pela UI (pode ser feito por migration manual se necessário)
- Filtro de abordagens por BPM
- Relatórios agrupados por BPM
- Múltiplos admins por BPM
