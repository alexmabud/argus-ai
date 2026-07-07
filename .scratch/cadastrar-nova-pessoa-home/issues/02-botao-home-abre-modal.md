Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## Blocked by

Issue 01 (componente compartilhado precisa existir).

## What to build

Adicionar um botão "Cadastrar Nova Pessoa" na home, abaixo do grid 2x2 de cards existente (Nova Abordagem / Consulta IA / Relatórios / Analítico), comprido e fino, largura igual à soma das duas colunas do grid, com estética consistente (glass/HUD tático) mas em formato de barra em vez de card quadrado. Ao clicar, abre o componente compartilhado do Issue 01 como modal teleportado (`x-teleport="body"`). Salvar cria a pessoa de verdade, usando o mesmo endpoint já usado pela Consulta IA.

## Acceptance criteria

- [ ] Botão aparece na home, abaixo do grid de 4 cards, com a largura das duas colunas somadas.
- [ ] Clicar no botão abre o modal com todos os campos do formulário de cadastro de pessoa.
- [ ] Preencher e clicar "SALVAR PESSOA" cria a pessoa via `POST /pessoas/` (mesmo comportamento do Issue 01).
- [ ] Fechar o modal (cancelar/X) limpa o formulário, igual ao comportamento já existente na Consulta IA.
- [ ] Pessoa criada por esse caminho aparece normalmente em buscas na Consulta IA.

## Verification

Manual em navegador real: na home, clicar no botão, preencher e salvar uma pessoa de teste; confirmar que ela aparece na busca da Consulta IA logo em seguida.
