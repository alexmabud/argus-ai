## Parent

[.scratch/deteccao-duplicidade-pessoa/spec.md](../spec.md)

## What to build

Estende o mesmo painel de aviso do slice 1 para também disparar a partir do campo `cpf`: ao completar um CPF válido (11 dígitos, já passando pela validação client-side existente `validarCPF`), dispara a mesma busca (`GET /consultas/?q=<cpf>&tipo=pessoa`, que já resolve match exato via `cpf_hash` quando a query parece CPF) e alimenta o mesmo painel/estado criado no slice 1 — sem duplicar a lógica de renderização do card. Diferente do campo nome, não precisa de debounce por caractere: só dispara quando o CPF fica completo/válido (buscar com CPF incompleto não teria retorno útil, já que o hash exige o valor exato).

Também cobre o teste de regressão do bloqueio duro existente: CPF exatamente igual a um já cadastrado deve continuar impedindo o submit com erro 409 (comportamento inalterado, só confirmação de que a nova busca em tempo real não interferiu nesse fluxo).

## Acceptance criteria

- [ ] Completar CPF válido de pessoa já cadastrada exibe o painel com o card daquela pessoa (mesmo componente do slice 1).
- [ ] Completar CPF válido sem cadastro correspondente não exibe o painel.
- [ ] Apagar/editar o CPF depois de completo atualiza ou limpa o painel corretamente (não fica um card "fantasma" de uma busca antiga).
- [ ] Painel populado por CPF não bloqueia preencher/submeter o formulário (mesma regra soft do slice 1).
- [ ] Tentar salvar com CPF exatamente igual a um já cadastrado continua bloqueado com 409 (regressão do comportamento já existente, não uma feature nova).
- [ ] Funciona nos dois pontos de entrada do modal, igual ao slice 1.

## Blocked by

- Slice 1 (`01-deteccao-por-nome.md`) — reaproveita o painel, o estado de candidatos e a chamada ao endpoint criados ali.

## Verification

Com `make dev` no ar, testar em navegador real (per CLAUDE.md):
- Completar CPF de pessoa já cadastrada → painel aparece com o card certo.
- Completar CPF novo (sem cadastro) → painel não aparece.
- Editar um CPF completo para outro valor → painel atualiza (ou some) corretamente.
- Tentar salvar com CPF idêntico a um já cadastrado → bloqueado com 409, como hoje.
- Repetir nos dois pontos de entrada (home e Consulta IA).
- `make lint`.
