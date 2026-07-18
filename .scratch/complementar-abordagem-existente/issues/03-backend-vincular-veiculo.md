---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Mesmo padrão do slice 02, para veículo: expor `POST /abordagens/{abordagem_id}/veiculos` e `DELETE /abordagens/{abordagem_id}/veiculos/{veiculo_id}`, reaproveitando `AbordagemService.vincular_veiculo`/`desvincular_veiculo`, com a mesma trava de autorização (dono ou admin) e a mesma correção de duplicidade/reativação de soft-delete que o slice 02 aplicou para pessoa (checar `uq_abordagem_veiculo`).

## Acceptance criteria

- [ ] Dono da abordagem vincula veículo já cadastrado via `POST /abordagens/{id}/veiculos` e aparece em `GET /abordagens/{id}`.
- [ ] Admin da guarnição consegue vincular veículo em abordagem de outro oficial.
- [ ] Terceiro (não dono, não admin) recebe 403.
- [ ] Vincular veículo já vinculado (ativo) retorna erro claro, não 500/constraint violation.
- [ ] Vincular veículo com vínculo soft-deleted anterior reativa em vez de duplicar.
- [ ] `DELETE /abordagens/{id}/veiculos/{veiculo_id}` desvincula respeitando a mesma trava.
- [ ] Audit log (`CREATE`/`DELETE` em `abordagem_veiculo`) continua sendo registrado.

## Blocked by

01-trava-autorizacao-patch (reaproveita o helper de autorização). Pode rodar em paralelo com 02, mas recomenda-se seguir depois para reaproveitar o padrão de teste já validado.

## Verification

Testes de unidade/integração no service (`vincular_veiculo`, duplicidade, reativação, `desvincular_veiculo`) e nos endpoints (dono/admin/terceiro). `make test` e `make lint` verdes.
