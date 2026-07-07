Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## What to build

Extrair o formulário "Cadastrar Pessoa" — hoje embutido inline em `consulta.js` (estado `novaPessoa`, seleção de estado/cidade/bairro com autocomplete e "+ Cadastrar", upload de foto, `criarPessoa()`) — para um componente compartilhado em `frontend/js/components/`, replicando o padrão de `person-photo-modal.js` (uma função de template `*HTML()` + uma função mixin de estado/métodos, mesclável via spread `{...}`). `consulta.js` passa a consumir esse componente novo no lugar do bloco inline. Nenhum comportamento ou aparência deve mudar para quem usa a Consulta IA hoje.

## Acceptance criteria

- [ ] Novo arquivo de componente compartilhado existe e exporta template + mixin de estado/métodos do formulário de cadastro de pessoa.
- [ ] `consulta.js` usa o componente novo; o bloco inline antigo é removido (sem duplicar a lógica).
- [ ] Fluxo atual da Consulta IA (buscar pessoa inexistente → "Cadastrar" → preencher todos os campos → "SALVAR PESSOA") funciona idêntico ao comportamento pré-extração: validação de CPF, autocomplete de cidade/bairro com opção "+ Cadastrar", upload de foto, mensagens de erro.
- [ ] Pessoa criada por esse fluxo aparece normalmente em buscas subsequentes (mesmo endpoint `POST /pessoas/`).

## Blocked by

None — pode começar imediatamente.

## Verification

Manual em navegador real (`make dev`): repetir o fluxo de busca sem resultado → Cadastrar → preencher → salvar, comparando com o comportamento de hoje (sem regressão). Conferir que a pessoa criada aparece em nova busca.
