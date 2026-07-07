Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## Blocked by

Nenhum tecnicamente — referencia apenas o botão criado no Issue 02, mas não depende do código dele. Sugerido rodar por último para linkar o botão real.

## What to build

Dentro do fluxo de Nova Abordagem, no bloco "Nenhuma pessoa encontrada" (onde já existe o botão "+ Cadastrar novo abordado"), adicionar um aviso avisando que, se o usuário só quer cadastrar uma pessoa sem registrar uma abordagem, deve usar o botão "Cadastrar Nova Pessoa" da home — com um link/ação que navega para lá.

## Acceptance criteria

- [ ] Bloco "Nenhuma pessoa encontrada" de Nova Abordagem mostra o aviso novo, ao lado do "+ Cadastrar novo abordado" existente (que continua funcionando sem mudanças).
- [ ] O link do aviso navega para a home.
- [ ] Nenhuma mudança no comportamento existente de "+ Cadastrar novo abordado" (continua salvando localmente até o envio da abordagem, conforme decisão da spec).

## Verification

Manual em navegador real: em Nova Abordagem, buscar uma pessoa inexistente, confirmar que o aviso aparece junto ao "+ Cadastrar novo abordado", e que o link navega para a home.
