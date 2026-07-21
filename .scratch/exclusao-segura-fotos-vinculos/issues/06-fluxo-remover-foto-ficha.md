---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Em `pessoa-detalhe.js`, seções "Foto de Rosto/Perfil" e "Fotos Relacionadas ao Abordado" (incluindo o modal "Ver mais", `modalTodasFotos`): remover o "✕" `x-show="isAdmin"` que hoje fica direto na miniatura da foto.

O modal local de foto ampliada (`fotoAmpliada`, distinto do `personPhotoModal` — é o bloco simples com imagem + dados da pessoa abaixo, sem header/footer) ganha um ícone de lixeira discreto no canto superior direito, visível só para `isAdmin` (permissão permanece admin-only, sem mudança de backend/modelo). Clicar na lixeira abre o componente de confirmação da issue 02; confirmar chama `DELETE /fotos/{foto_id}` (já existente, `FotoService.desativar`) e atualiza a lista de fotos local.

## Acceptance criteria

- [ ] Miniaturas de foto de rosto e de evidência não têm mais "✕", nem no grid principal nem no modal "Ver mais".
- [ ] Ampliar qualquer uma dessas fotos mostra a lixeira só se `isAdmin` for verdadeiro.
- [ ] Clicar na lixeira abre a confirmação customizada (issue 02); cancelar não apaga nada.
- [ ] Confirmar chama `DELETE /fotos/{foto_id}`, remove a foto da lista local correspondente (rosto ou evidência) e fecha o modal ampliado.
- [ ] Usuário não-admin não vê a lixeira em nenhum ponto (miniatura ou foto ampliada).

## Blocked by

02-componente-modal-confirmacao. Pode rodar em paralelo com 03/04/05.

## Verification

Teste e2e Playwright cobrindo: admin apaga foto de rosto e de evidência via foto ampliada com confirmação, não-admin não vê a lixeira em nenhum dos dois grids nem no modal "Ver mais". `make test` verde.
