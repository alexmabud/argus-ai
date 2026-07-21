---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Em `abordagem-detalhe.js`, remover o botão "✕" que hoje fica direto na miniatura da pessoa no card "Abordados". A remoção passa a acontecer só a partir do modal "Foto Ampliada" (`personPhotoModal`, `frontend/js/components/person-photo-modal.js`).

Estender `personPhotoModal`/`openPhotoModal(...)` com um parâmetro explícito de contexto de exclusão (não inferir pela página) — algo como `openPhotoModal(photoUrl, pessoaId, previewData, veiculoData, deleteContext)`, onde `deleteContext` descreve a ação disponível (ex.: `{ tipo: 'abordado', abordagemId, pessoaId }`) e só é passado pelas telas que devem oferecer exclusão. Quando `deleteContext` está presente **e** o usuário tem permissão (`podeEditar()` já existente em `abordagem-detalhe.js`), o modal mostra um ícone de lixeira discreto no canto superior direito. Clicar na lixeira abre o componente de confirmação da issue 02; confirmar chama `DELETE /abordagens/{id}/pessoas/{pessoa_id}` e atualiza `ab.pessoas` localmente sem recarregar a página.

Importante: as demais chamadas existentes de `openPhotoModal` (dashboard, consulta, relacionamentos/vínculos em `pessoa-detalhe.js`) não passam `deleteContext` e continuam sem exibir lixeira nenhuma — comportamento inalterado.

## Acceptance criteria

- [ ] Miniatura de abordado na tela de abordagem não tem mais "✕".
- [ ] Abrir a foto ampliada de um abordado mostra a lixeira só se `podeEditar()` for verdadeiro para a abordagem atual.
- [ ] Clicar na lixeira abre a confirmação customizada (issue 02); cancelar não remove nada e mantém o modal ou fecha só a confirmação.
- [ ] Confirmar chama `DELETE /abordagens/{id}/pessoas/{pessoa_id}`, remove a pessoa de `ab.pessoas` no estado local e fecha o modal.
- [ ] Usuário sem permissão (não dono, não admin) que abre a foto ampliada não vê a lixeira.
- [ ] `personPhotoModal` aberto a partir de dashboard, consulta ou seções de relacionamento/vínculo em `pessoa-detalhe.js` continua sem lixeira (regressão zero nesses usos).

## Blocked by

02-componente-modal-confirmacao.

## Verification

Teste e2e Playwright cobrindo: dono/admin remove abordado via foto ampliada com confirmação, terceiro não vê a lixeira, cancelar na confirmação não remove. Smoke check manual de que os outros usos de `personPhotoModal` (dashboard/consulta) seguem sem lixeira. `make test` verde.
