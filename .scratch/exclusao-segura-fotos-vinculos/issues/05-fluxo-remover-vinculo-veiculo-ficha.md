---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Em `pessoa-detalhe.js`, seção "Veículos Vinculados ao Abordado": remover o ícone de remoção direto do card (hoje visível só para `v.origem === 'direto'`, com `confirm()` nativo, sem checar dono/admin). A remoção passa a acontecer só a partir do `personPhotoModal` ampliado do veículo (já usado nessa mesma tela via `openPhotoModal(fv.arquivo_url, pessoa.id, pessoa, v)`).

Usar o mesmo padrão de `deleteContext` das issues 03/04, agora para o vínculo pessoa-veículo: `{ tipo: 'veiculo-pessoa', pessoaId, veiculoId }`. O ícone de lixeira só aparece se `v.origem === 'direto'` (mantém a regra atual de que só vínculos diretos podem ser desfeitos por aqui, não os derivados de abordagem) **e** o usuário for dono do vínculo (`criado_por_id`) ou admin — a nova permissão da issue 01. Confirmar chama `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` e atualiza a lista `veiculos` local.

## Acceptance criteria

- [ ] Card de veículo em "Veículos Vinculados ao Abordado" não tem mais ícone de remoção direto.
- [ ] Abrir a foto ampliada de um veículo com `origem === 'direto'` mostra a lixeira só se o usuário logado for o dono do vínculo ou admin (403 do backend nunca deveria ser alcançável pela UI, mas a UI já esconde antes).
- [ ] Veículo com `origem` diferente de `'direto'` (derivado de abordagem) nunca mostra a lixeira nessa tela, mesmo para admin.
- [ ] Confirmar remoção chama `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}`, remove o veículo da lista local `veiculos` e fecha o modal.
- [ ] Usuário autenticado da guarnição que não é dono do vínculo nem admin não vê a lixeira (reflete a permissão apertada na issue 01).

## Blocked by

01-backend-permissao-vinculo-veiculo, 04-fluxo-remover-veiculo-da-abordagem (reaproveita o wiring de foto ampliada de veículo).

## Verification

Teste e2e Playwright cobrindo: dono do vínculo remove com confirmação, admin remove vínculo de outro usuário, terceiro autenticado da guarnição não vê a lixeira, veículo `origem` não-direto nunca mostra a lixeira. `make test` verde.
