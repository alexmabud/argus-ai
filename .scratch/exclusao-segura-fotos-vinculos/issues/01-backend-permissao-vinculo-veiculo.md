---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Apertar a autorização de `PessoaVeiculoService.desvincular` (usado por `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` em `app/api/v1/pessoas.py`). Hoje qualquer usuário autenticado da guarnição consegue desvincular; passa a exigir que o usuário seja o dono do vínculo (`PessoaVeiculo.criado_por_id == user.id`) ou admin/super-admin (`user.is_admin`/`user.is_super_admin`).

Extrair a checagem para um helper reutilizável em `app/core/permissions.py`, seguindo o padrão já existente de `assert_pode_editar_abordagem` (mesmo arquivo) — ex.: `assert_pode_remover_vinculo_veiculo(user, vinculo)`. Não duplicar a lógica inline no service.

## Acceptance criteria

- [ ] Usuário que criou o vínculo (`criado_por_id == user.id`) consegue desvincular normalmente (comportamento hoje preservado para esse caso).
- [ ] Admin da guarnição (`is_admin=True` ou `is_super_admin=True`) consegue desvincular vínculo criado por outro usuário.
- [ ] Usuário autenticado da mesma guarnição que **não** é dono do vínculo nem admin recebe 403 com mensagem clara (hoje não recebe — este é o comportamento novo).
- [ ] Helper de autorização isolado e testável, não lógica solta no service.
- [ ] Audit log da remoção continua sendo registrado como hoje.

## Blocked by

None — pode começar imediatamente.

## Verification

Testes de integração em `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` cobrindo os três casos (dono do vínculo, admin, terceiro → 403). `make test` e `make lint` verdes.
