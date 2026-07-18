---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Adicionar checagem de autorização ao `PATCH /abordagens/{abordagem_id}` (endpoint `atualizar_abordagem` em `app/api/v1/abordagens.py` / `AbordagemService.atualizar`): só o `usuario_id` dono da abordagem, ou um admin da guarnição (`user.is_admin` ou `user.is_super_admin`), pode chamar. Qualquer outro usuário recebe 403.

Extrair a checagem para um helper reutilizável (ex.: em `app/core/permissions.py`, seguindo o padrão já existente de `assert_scope`), pois os próximos slices (vincular/desvincular pessoa e veículo) vão precisar da mesma regra.

## Acceptance criteria

- [ ] Dono da abordagem consegue chamar `PATCH /abordagens/{id}` normalmente (comportamento hoje preservado).
- [ ] Admin da guarnição (`is_admin=True` ou `is_super_admin=True`) consegue chamar `PATCH /abordagens/{id}` de abordagem de outro oficial da mesma guarnição.
- [ ] Usuário que não é dono nem admin recebe 403 com mensagem clara.
- [ ] Helper de autorização isolado e testável (não é lógica solta duplicada no router).

## Blocked by

None — pode começar imediatamente.

## Verification

Testes de integração no endpoint `PATCH /abordagens/{id}` cobrindo os três casos (dono, admin, terceiro → 403). `make test` e `make lint` verdes.
