---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Mesmo padrão dos slices 04+05, para veículo: botão "+ Adicionar veículo" no card "Veículos" da tela de detalhe, com autocomplete de veículo já cadastrado (`autocompleteComponent('veiculo')`) e opção de cadastro inline de veículo novo, chamando `POST /abordagens/{id}/veiculos`. Ação de remover veículo vinculado via `DELETE /abordagens/{id}/veiculos/{veiculo_id}`. Mesma checagem de visibilidade (dono ou admin) dos slices anteriores.

## Acceptance criteria

- [ ] Dono/admin conseguem adicionar veículo já cadastrado ou cadastrar um novo inline, vinculado à abordagem aberta.
- [ ] Terceiro não vê/não consegue usar o botão.
- [ ] Remover veículo vinculado funciona e reflete no estado local.
- [ ] Erros da API exibidos de forma legível.

## Blocked by

03-backend-vincular-veiculo, 04-frontend-adicionar-remover-pessoa-existente (reaproveita o padrão de UI/permissão já validado).

## Verification

Teste e2e Playwright cobrindo adicionar veículo existente, cadastrar veículo novo inline, remover veículo, e bloqueio para terceiro. `make test` verde.
