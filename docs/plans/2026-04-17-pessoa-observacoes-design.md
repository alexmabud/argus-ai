# Design: Observações na Ficha do Abordado

**Data:** 2026-04-17
**Status:** Aprovado

## Contexto

A ficha do abordado (`pessoa-detalhe.js`) exibe vários containers de informação (dados pessoais, fotos, endereços, veículos, vínculos, histórico de abordagens). O objetivo é adicionar um container de **observações livres** vinculadas à pessoa, com histórico cronológico, abaixo do container de vínculos.

## Decisão de Design

Opção escolhida: **nova tabela `pessoa_observacoes`**, seguindo o mesmo padrão de `enderecos` e `vinculos-manuais` já presentes no projeto.

## Backend

### Modelo `PessoaObservacao`

Nova tabela `pessoa_observacoes` com:
- `id` (UUID PK)
- `pessoa_id` (FK → pessoas.id)
- `texto` (Text, not null)
- `garrison_id` (multi-tenancy)
- Mixins: `TimestampMixin` (created_at, updated_at) + `SoftDeleteMixin` (deleted_at)

### Schemas Pydantic

- `PessoaObservacaoCreate` — campo `texto`
- `PessoaObservacaoUpdate` — campo `texto`
- `PessoaObservacaoResponse` — `id`, `texto`, `created_at`

### Endpoints

Base: `/api/v1/pessoas/{pessoa_id}/observacoes`

| Método | Path | Ação |
|--------|------|------|
| GET | `/` | Lista observações ativas da pessoa |
| POST | `/` | Cria nova observação |
| PATCH | `/{obs_id}` | Edita texto da observação |
| DELETE | `/{obs_id}` | Soft delete da observação |

Todas as ações registradas no `AuditService`.

### Arquivos a criar/modificar

- `app/models/pessoa_observacao.py` — novo modelo
- `app/schemas/pessoa_observacao.py` — schemas Pydantic
- `app/repositories/pessoa_observacao_repository.py` — queries
- `app/services/pessoa_observacao_service.py` — lógica de negócio
- `app/api/v1/pessoas.py` — novos endpoints (sub-router)
- `app/models/__init__.py` — exportar novo modelo
- migration Alembic

## Frontend

### Container

- Posição: abaixo do container de vínculos em `pessoa-detalhe.js`
- Estilo: `glass-card card-led-blue` (mesmo padrão dos outros containers)
- Header: título "Observações" + botão `+ Nova Observação`
- Estado vazio: mensagem estilizada quando não há observações

### Cada item de observação

- Data de criação (`created_at`) no canto superior direito
- Texto da observação
- Botão editar (ícone lápis, visível no hover) → abre modal de edição
- Botão deletar (ícone X, visível no hover) → confirmação antes de deletar

### Modal

- Único modal reutilizado para criar e editar
- Campo `textarea` para o texto
- Botões: Cancelar / Salvar
- Spinner durante submit

### Métodos Alpine.js

Adicionados ao objeto `pessoaDetalhePage`:
- `carregarObservacoes()` — chamado no `init()`
- `abrirModalObservacao(obs = null)` — null = criar, objeto = editar
- `salvarObservacao()` — POST (criar) ou PATCH (editar)
- `deletarObservacao(obsId)` — DELETE com confirmação

### API calls

- `GET /pessoas/{pessoaId}/observacoes`
- `POST /pessoas/{pessoaId}/observacoes`
- `PATCH /pessoas/{pessoaId}/observacoes/{obsId}`
- `DELETE /pessoas/{pessoaId}/observacoes/{obsId}`
