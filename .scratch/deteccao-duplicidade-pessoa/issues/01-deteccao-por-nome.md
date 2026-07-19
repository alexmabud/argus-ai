## Parent

[.scratch/deteccao-duplicidade-pessoa/spec.md](../spec.md)

## What to build

No modal de cadastro de pessoa (`cadastro-pessoa-modal.js`), busca em tempo real enquanto o operador digita no campo `nome`: debounce ~400ms, mínimo 3 caracteres, chama `GET /consultas/?q=...&tipo=pessoa` (endpoint já existente, fuzzy pg_trgm). Se encontrar candidato(s), renderiza um painel inline "Possível pessoa já cadastrada" logo abaixo do campo, com um card por candidato (até ~5) reaproveitando o layout já usado em `pessoaPreview`/cards de `consulta.js` (foto ou placeholder, nome, apelido, CPF mascarado, data de nascimento). Clicar num card navega para a ficha completa da pessoa (`viewPessoa(id)`). O painel é puramente informativo — não impede preencher o resto do formulário nem submeter.

Novo estado necessário em `cadastroPessoaModal()`: lista de candidatos, timer de debounce, flag de carregando/erro da busca — sem interferir no estado existente do formulário.

## Acceptance criteria

- [ ] Digitar nome (≥3 chars) de pessoa já cadastrada exibe o painel com card(s) correspondente(s), após ~400ms sem digitar.
- [ ] Digitar nome parecido (variação/apelido) também retorna candidato(s) plausíveis (fuzzy).
- [ ] Digitar nome sem correspondência não exibe o painel (ou exibe estado vazio, sem erro visual).
- [ ] Card mostra foto/placeholder, nome, apelido, CPF mascarado, data de nascimento — mesmo padrão visual usado no resto do app.
- [ ] Clicar num card navega para a ficha completa da pessoa correta.
- [ ] Painel não bloqueia preencher/submeter o formulário; cadastro de pessoa nova continua funcionando normalmente com o painel visível.
- [ ] Funciona nos dois pontos de entrada do modal (botão "Cadastrar Nova Pessoa" da home e "Cadastrar" dentro de Consulta IA) sem lógica duplicada — por ser componente compartilhado.
- [ ] Sem regressão nos campos/fluxo existentes do modal (CPF, data nascimento, apelido, nome da mãe, endereço em cascata, upload de foto, submit).

## Blocked by

None — pode começar imediatamente.

## Verification

Com `make dev` no ar, testar em navegador real (per CLAUDE.md):
- Digitar nome de pessoa existente → painel aparece com o card certo.
- Digitar nome parecido → candidatos plausíveis aparecem.
- Digitar nome inexistente → painel não aparece.
- Clicar num card → navega pra ficha completa correta.
- Preencher e salvar pessoa nova com o painel visível (nome parecido mas pessoa diferente) → cadastro é criado normalmente, sem bloqueio.
- Repetir nos dois pontos de entrada (home e Consulta IA).
- `make lint`.
