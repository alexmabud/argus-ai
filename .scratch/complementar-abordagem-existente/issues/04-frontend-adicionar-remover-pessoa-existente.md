---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Na tela de detalhe da abordagem (`frontend/js/pages/abordagem-detalhe.js`), adicionar botão "+ Adicionar abordado" no card "Abordados". Visível/habilitado só quando o usuário logado é o dono da abordagem (`ab.usuario.id === auth.getUser().id`) ou admin (`isAdmin`, já calculado na página). Ao clicar, abre o componente de autocomplete de pessoa (`frontend/js/components/autocomplete.js`, `autocompleteComponent('pessoa')`) para buscar pessoa já cadastrada; ao selecionar, chama `POST /abordagens/{id}/pessoas` e atualiza `this.ab.pessoas` no estado local.

Adicionar também ação de remover (ex.: "×" no avatar/chip da pessoa ou botão dedicado) chamando `DELETE /abordagens/{id}/pessoas/{pessoa_id}`, com a mesma checagem de visibilidade.

Não incluir ainda o fluxo de "+ Cadastrar novo abordado" (cadastro inline de pessoa nova) — isso é o slice 05.

## Acceptance criteria

- [ ] Dono da abordagem vê o botão "+ Adicionar abordado", busca e seleciona pessoa já cadastrada, e ela aparece na lista de abordados sem recarregar a página manualmente.
- [ ] Admin vê e consegue usar o mesmo botão em abordagem de outro oficial.
- [ ] Usuário que não é dono nem admin não vê o botão (ou vê desabilitado, com feedback claro se tentar usar).
- [ ] Remover pessoa vinculada funciona e reflete no estado local imediatamente.
- [ ] Erros da API (403, 409 de duplicidade) são exibidos ao usuário de forma legível, não travam a tela.

## Blocked by

02-backend-vincular-pessoa.

## Verification

Teste e2e Playwright (seguindo o padrão de `tests/e2e/frontend/test_abordagem_nova_pessoas.py`) cobrindo: adicionar pessoa existente como dono, botão ausente/ação bloqueada para terceiro, remover pessoa vinculada. `make test` verde.
