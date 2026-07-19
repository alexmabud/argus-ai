---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Expor `POST /abordagens/{abordagem_id}/pessoas` e `DELETE /abordagens/{abordagem_id}/pessoas/{pessoa_id}` no router, reaproveitando `AbordagemService.vincular_pessoa`/`desvincular_pessoa` já existentes (hoje não chamados por nenhum router). Aplicar o helper de autorização do slice 01 (dono ou admin) nos dois endpoints.

Corrigir `vincular_pessoa` antes de expor: hoje ele insere um novo `AbordagemPessoa` sem checar se já existe vínculo (ativo ou soft-deleted) para o par `(abordagem_id, pessoa_id)`. Isso pode colidir com a constraint única `uq_abordagem_pessoa` (vínculo ativo duplicado) ou criar um registro novo em vez de reativar um soft-delete anterior. Tratar: se já existe vínculo ativo, retornar erro claro (409 ou equivalente) em vez de estourar a constraint; se existe vínculo soft-deleted, reativar (`ativo = True`) em vez de inserir linha nova.

Confirmar que a re-materialização de relacionamentos (`relacionamento.registrar_vinculo`) continua correta quando chamada por esses endpoints (idempotência ao vincular a mesma pessoa mais de uma vez ao longo do tempo).

## Acceptance criteria

- [ ] Dono da abordagem vincula pessoa já cadastrada via `POST /abordagens/{id}/pessoas` e o vínculo aparece em `GET /abordagens/{id}` (via `AbordagemDetail`/`_serializar_detalhe`).
- [ ] Admin da guarnição consegue vincular pessoa em abordagem de outro oficial.
- [ ] Terceiro (não dono, não admin) recebe 403.
- [ ] Vincular pessoa já vinculada (ativa) retorna erro claro, não 500/constraint violation.
- [ ] Vincular pessoa com vínculo soft-deleted anterior reativa o vínculo em vez de duplicar.
- [ ] `DELETE /abordagens/{id}/pessoas/{pessoa_id}` desvincula (soft delete) respeitando a mesma trava de autorização.
- [ ] Audit log (`CREATE`/`DELETE` em `abordagem_pessoa`) continua sendo registrado.

## Blocked by

01-trava-autorizacao-patch (reaproveita o helper de autorização).

## Verification

Testes de unidade/integração no service (`vincular_pessoa`, duplicidade, reativação, `desvincular_pessoa`) e nos endpoints (dono/admin/terceiro). `make test` e `make lint` verdes.
