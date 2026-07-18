---
status: ready-for-execution
---

## Parent

.scratch/complementar-abordagem-existente/spec.md

## What to build

Adicionar a opção "+ Cadastrar novo abordado" dentro do autocomplete de pessoa montado no slice 04 (mesmo padrão de `abordagem-nova.js`: quando a busca não encontra a pessoa, oferece cadastro inline). Abre o formulário completo de cadastro de pessoa (nome, CPF, endereço com selects em cascata, foto — mesmos campos de `abordagem-nova.js`) em modal/inline na própria tela de detalhe, sem navegar para outra página.

Avaliar se o formulário de `abordagem-nova.js` (função `criarPessoa()` e HTML associado, hoje acoplados ao estado da página de criação) pode ser extraído para um componente compartilhado, ou se é mais simples/seguro replicar o necessário dentro de `abordagem-detalhe.js` adaptado para vincular à abordagem já existente via `POST /abordagens/{id}/pessoas` (em vez de acumular em `pessoa_ids` para o payload de criação, como faz hoje). Preferir extração se não aumentar desproporcionalmente o escopo do slice; caso contrário, documentar a duplicação aceita.

## Acceptance criteria

- [ ] A partir da tela de detalhe, cadastrar pessoa nova inline funciona (mesmos campos/validações de `abordagem-nova.js`) e ela é vinculada automaticamente à abordagem aberta.
- [ ] Duplicação de detecção de pessoa (nome/CPF já existente) continua funcionando, se aplicável ao formulário reaproveitado (ver features recentes de detecção de duplicidade na branch atual).
- [ ] Fluxo não navega para fora da tela de detalhe.

## Blocked by

04-frontend-adicionar-remover-pessoa-existente.

## Verification

Teste e2e Playwright cobrindo cadastro de pessoa nova inline a partir do detalhe da abordagem e vínculo automático. `make test` verde.
