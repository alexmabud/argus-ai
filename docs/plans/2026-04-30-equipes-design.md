# Design: Gestão de Equipes (Guarnições)

**Data:** 2026-04-30
**Status:** Aprovado

## Contexto

O sistema usa o conceito de `guarnicao` internamente (banco de dados, modelos Python, APIs). No frontend e para o usuário final, esse conceito será chamado de **"Equipe"**. Não haverá renomeação de banco ou código — apenas labels na UI. As docstrings dos modelos documentam essa equivalência.

Atualmente todos os usuários foram atribuídos a uma guarnição genérica para não quebrar a lógica existente. O objetivo é voltar a dividir os policiais por equipe real, com gestão facilitada pelo admin.

## Decisões de Design

- **Sem renomeação de banco/código** — `guarnicao`/`guarnicao_id` permanecem. UI exibe "Equipe".
- **Sem script de migração** — a aba "Sem Equipe" resolve organicamente.
- **Toggle de isolamento** — nova coluna `isolamento_abordagens` na tabela `guarnicoes`. Pessoas abordadas sempre visíveis para todos.

## Modelo de Dados

### Alteração em `guarnicoes`

```sql
ALTER TABLE guarnicoes
ADD COLUMN isolamento_abordagens BOOLEAN NOT NULL DEFAULT FALSE;
```

- `False` (padrão) → equipe vê abordagens de todo o sistema
- `True` → equipe vê apenas abordagens da própria equipe

### Lógica no AbordagemService

```python
if usuario.guarnicao.isolamento_abordagens:
    query = TenantFilter.apply(query, Abordagem, usuario)
# else: sem filtro de equipe
```

## Novos Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/admin/equipes` | Criar nova equipe |
| `PATCH` | `/admin/equipes/{id}/toggle-isolamento` | Ligar/desligar isolamento de abordagens |
| `PATCH` | `/admin/usuarios/{id}/equipe` | Mover usuário para outra equipe (ou remover de equipe) |

## Frontend — Página Gerenciar Usuários

### Estrutura de Abas

```
[ Sem Equipe (N) ]  [ GU-01 ]  [ GU-02 ]  ...  [ + Nova Equipe ]
```

#### Aba "Sem Equipe"
- Lista usuários com `guarnicao_id = null`
- Cada card de usuário tem select de equipe + botão "Atribuir à equipe"
- Serve como solução orgânica para migração dos usuários existentes

#### Abas por Equipe
- Header da aba: nome da equipe + toggle on/off de isolamento de abordagens
- Toggle: "Ver apenas abordagens desta equipe" (on/off visual, visível uma vez no topo da aba)
- Cards de usuário com todos os botões existentes (Pausar, Gerar senha, Excluir)
- Cada card tem adicionalmente: select de equipe + botão "Mover para equipe"

#### Aba "+ Nova Equipe"
- Mini-form inline: campos `nome` e `unidade`
- Ao criar, aba nova aparece selecionada

### Modal de Criação de Usuário
- Campo adicional: **"Equipe"** — select com equipes existentes
- Opção "Sem equipe" disponível como fallback
- Ao selecionar "+ Nova equipe", expande campos para criação inline

## Fluxo de Migração (sem script)

1. Admin acessa "Gerenciar Usuários"
2. Aba "Sem Equipe" exibe todos os usuários sem `guarnicao_id`
3. Admin cria as equipes reais via "+ Nova Equipe"
4. Atribui cada usuário à equipe correta via select
5. Concluído — sem migration, sem script externo

## Escopo Fora deste Design

- Renomeação de `guarnicao` → `equipe` no banco/código (decisão: manter como está, documentar)
- Isolamento de pessoas abordadas por equipe (todos sempre veem)
- Gestão de equipes além de criar (editar nome/unidade, excluir equipe)
