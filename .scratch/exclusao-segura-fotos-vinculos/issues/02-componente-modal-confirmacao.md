---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Criar um componente de modal de confirmação customizado e reutilizável em `frontend/js/components/` (ex.: `confirm-dialog.js`), seguindo o estilo visual já usado nos outros modais do app (glass-card, cores do tema, `x-teleport="body"` como em `person-photo-modal.js`). Deve aceitar uma mensagem parametrizável (ex.: "Remover este abordado? Esta ação não pode ser desfeita.") e expor uma forma de disparar confirmar/cancelar (ex.: `confirmarAcao(mensagem, callback)` ou API baseada em Promise) para ser chamado por qualquer página que já misture `x-data` com esse componente, no mesmo padrão de `personPhotoModal()`/`personPhotoModalHTML()`.

Este componente é puramente de UI — sem lógica de negócio, sem chamadas à API. As páginas que o consumirem (slices seguintes) decidem o que fazer quando confirmado.

## Acceptance criteria

- [ ] Componente abre com uma mensagem customizada e dois botões (confirmar/cancelar), visualmente consistente com os demais modais do app.
- [ ] Confirmar dispara o callback/resolve fornecido pelo chamador; cancelar fecha o modal sem disparar nada.
- [ ] Clicar fora do modal ou apertar Esc (se os outros modais do app já tiverem esse comportamento) fecha sem confirmar.
- [ ] Reutilizável por múltiplas páginas via `x-data="{ ...outraPage(), ...confirmDialog() }"`, sem estado global compartilhado indevidamente entre chamadas.

## Blocked by

None — pode começar imediatamente.

## Verification

Sem consumidor próprio ainda nesta issue — verificado via smoke test manual (abrir/confirmar/cancelar) e, de forma mais completa, pelo teste e2e do primeiro fluxo que o consome (issue 03). `make lint` verde.
