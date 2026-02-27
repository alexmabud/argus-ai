# ADR 001 — Arquitetura Offline-First

## Status
Aceito

## Contexto
Equipes de patrulhamento operam em áreas com conexão instável ou inexistente. O sistema precisa funcionar sem internet e sincronizar quando a conexão retornar, sem perda de dados.

## Decisão
Adotar arquitetura offline-first com IndexedDB (Dexie.js) no frontend e endpoint de sync batch no backend.

### Componentes
- **IndexedDB via Dexie.js**: Armazena fila de sincronização e cache local de pessoas/veículos
- **Service Worker**: Cache-first para assets, network-first para API
- **SyncManager**: Poll a cada 30s quando online, escuta evento `online`
- **POST /sync/batch**: Endpoint backend que processa itens em batch com deduplicação por `client_id`

### Deduplicação
Cada item offline recebe um `client_id` (UUID v4). O backend verifica se já existe registro com o mesmo `client_id` antes de criar, garantindo idempotência.

## Consequências
- Toda ação pode ser completada sem internet
- Dados nunca são perdidos por falta de conexão
- Complexidade adicional no gerenciamento de conflitos
- Frontend precisa manter cache local atualizado
