# Design: Filtro de Abordagens por BPM

**Data:** 2026-05-03  
**Status:** Aprovado  
**Contexto:** Argus AI — Sistema de apoio operacional

## Problema

O sistema já possui um filtro por equipe (`isolamento_abordagens` em `guarnicoes`) que restringe a visualização de abordagens à equipe do usuário. A demanda é adicionar um segundo filtro no nível BPM, criando dois filtros em cascata:

1. **Filtro de equipe** — usuário vê apenas abordagens da sua equipe (pelotão)
2. **Filtro de BPM** — usuário vê apenas abordagens do seu BPM

## Regra de Negócio

Prioridade em cascata (mais restritivo prevalece):

| Filtro equipe | Filtro BPM | Resultado |
|---|---|---|
| ON | qualquer | Filtra por `guarnicao_id` |
| OFF | ON | Filtra por `bpm_id` (via JOIN) |
| OFF | OFF | Global (sem filtro) |

- Usuário sem BPM com filtro BPM ativo → vê **zero** abordagens
- Filtro de equipe sempre prevalece sobre filtro de BPM

## Abordagem Escolhida

**JOIN direto no repo** via `guarnicoes.bpm_id`. Sem desnormalização de dados, query eficiente com índice existente, segue o mesmo padrão do filtro de equipe.

## Mudanças por Camada

### Banco de Dados

- **Migration nova:** `bpms.isolamento_abordagens` (Boolean, NOT NULL, DEFAULT False)
- **Carregamento:** garantir `selectin` em cascata `Usuario.guarnicao → Guarnicao.bpm`

### Backend

**Schemas Pydantic:**
- `BpmRead` — adiciona campo `isolamento_abordagens: bool`
- `BpmIsolamentoUpdate` — schema novo: `{ isolamento_abordagens: bool }`

**Service — `BpmService`:**
- Método `toggle_isolamento(bpm_id, valor)` — equivalente ao de `EquipeService`

**API Admin:**
- `PATCH /admin/bpms/{bpm_id}/toggle-isolamento` — endpoint novo em `app/api/v1/admin/bpms.py`

**Helper de filtro (substitui `_isolamento()` nos routers):**
```python
def _filtro_abordagem(user) -> tuple[str, int | None]:
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return ("guarnicao", user.guarnicao_id)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return ("bpm", user.guarnicao.bpm_id)
    return ("global", None)
```

Routers afetados: `abordagens.py`, `analytics.py`, `consultas.py`

**Repositório — `AbordagemRepo`:**

Novas variantes com JOIN em `guarnicoes.bpm_id`:
- `list_by_bpm(bpm_id)`
- `list_by_data_by_bpm(bpm_id, data_inicio, data_fim)`
- `search_by_texto_by_bpm(bpm_id, texto)`
- `get_detail_by_bpm(abordagem_id, bpm_id)`

**Service — `AbordagemService`:**

Cada método substitui `isolamento: bool` por `filtro: tuple[str, int | None]`:
```python
match filtro:
    case ("guarnicao", id): return await repo.list_by_guarnicao(id)
    case ("bpm", id):       return await repo.list_by_bpm(id)
    case _:                 return await repo.list_global()
```

### Frontend

**Arquivo:** `frontend/js/pages/admin-usuarios.js`

- Toggle "Ver apenas abordagens do BPM" no cabeçalho do BPM ativo
- Posição: simétrica ao toggle de equipe (canto superior direito do painel do BPM)
- `bpmAtivoObj` inclui `isolamento_abordagens` (vindo do `GET /admin/bpms`)
- Nova função `alternarIsolamentoBpm(bpmId, valor)` → `PATCH /admin/bpms/{id}/toggle-isolamento`

## Arquivos Afetados

| Arquivo | Tipo de mudança |
|---|---|
| `alembic/versions/` | Nova migration |
| `app/models/bpm.py` | Campo `isolamento_abordagens` |
| `app/models/guarnicao.py` | Garantir `selectin` em `bpm` |
| `app/schemas/bpm.py` | `BpmRead` + `BpmIsolamentoUpdate` |
| `app/services/bpm_service.py` | `toggle_isolamento()` |
| `app/services/abordagem_service.py` | Troca `isolamento: bool` → `filtro: tuple` |
| `app/repositories/abordagem_repo.py` | 4 variantes `*_by_bpm` |
| `app/api/v1/admin/bpms.py` | Endpoint `toggle-isolamento` |
| `app/api/v1/abordagens.py` | Helper `_filtro_abordagem()` |
| `app/api/v1/analytics.py` | Helper `_filtro_abordagem()` |
| `app/api/v1/consultas.py` | Helper `_filtro_abordagem()` |
| `frontend/js/pages/admin-usuarios.js` | Toggle BPM + `alternarIsolamentoBpm()` |
