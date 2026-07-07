Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## Blocked by

Issue 02 (modal da home precisa existir para receber o aviso).

## What to build

Adicionar, apenas quando o modal compartilhado é aberto a partir do botão da home (não na Consulta IA — confirmado com o usuário), um aviso vermelho fixo no topo do modal, bem chamativo, com uma frase direta avisando que aquele formulário cadastra uma **pessoa**, não uma abordagem, e que quem quiser registrar uma abordagem deve usar o botão "Nova Abordagem". A parte "Nova Abordagem" da frase é um link/ação que fecha o modal e navega para a página `abordagem-nova`.

## Acceptance criteria

- [ ] Modal aberto pela home mostra o aviso vermelho no topo, visualmente destacado (cor/contraste chamam atenção).
- [ ] Modal aberto pela Consulta IA **não** mostra esse aviso — continua idêntico ao Issue 01.
- [ ] O link "Nova Abordagem" dentro da frase fecha o modal e navega para a página de Nova Abordagem.

## Verification

Manual em navegador real: abrir o modal pela home, confirmar aviso visível; clicar no link e confirmar navegação para Nova Abordagem com o modal fechado. Reabrir pela Consulta IA e confirmar que o aviso não aparece lá.
