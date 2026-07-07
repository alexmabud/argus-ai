# Spec

## Problem

Cadastrar uma pessoa sem vínculo a uma abordagem hoje só é possível por um caminho pouco visível: dentro de "Consulta IA", buscar por nome/CPF e, somente depois de a busca não retornar resultado, aparece um link textual discreto "Cadastrar" ([consulta.js:184-189](frontend/js/pages/consulta.js#L184-L189)). Não existe nenhum ponto de entrada para essa função na home.

Como consequência, usuários usam o fluxo de "Nova Abordagem" — que tem um atalho muito mais visível ("+ Cadastrar novo abordado", direto no dropdown de busca de pessoa, [abordagem-nova.js:51-58](frontend/js/pages/abordagem-nova.js#L51-L58)) — só para cadastrar uma pessoa, mesmo quando não pretendem registrar uma abordagem de verdade.

## Scope

- Novo botão na home ("Cadastrar Nova Pessoa"), comprido/fino, abaixo do grid 2x2 atual de cards ([app.js:592-651](frontend/js/app.js#L592-L651)), largura = as duas colunas somadas.
- Extrair o formulário "Cadastrar Pessoa" hoje embutido em `consulta.js` (~[L192-322](frontend/js/pages/consulta.js#L192-L322)) para um componente compartilhado, seguindo o padrão já usado em [person-photo-modal.js](frontend/js/components/person-photo-modal.js#L17) (`*HTML()` para template + mixin de estado/métodos mesclado via spread). Reaproveitado por Consulta IA (comportamento atual preservado) e pelo novo botão da home (como modal de verdade, teleportado).
- Aviso vermelho, fixo no topo do modal: deixa claro que aquele campo cadastra uma **pessoa**, não uma abordagem, com link/ação que navega para "Nova Abordagem".
- Aviso espelhado dentro do bloco "Nenhuma pessoa encontrada" de Nova Abordagem, com link/ação para o novo botão "Cadastrar Nova Pessoa" da home.

## Out of scope

- Qualquer mudança no comportamento interno de Nova Abordagem — o array local `novasPessoas` e o timing de persistência (só grava no envio da abordagem inteira, [abordagem-nova.js:778](frontend/js/pages/abordagem-nova.js#L778)) é **intencional** (evita pessoa órfã se o envio da abordagem falhar no meio), confirmado com o usuário. Não tocar.
- Qualquer mudança de regra de negócio ou endpoint no backend (`/pessoas/` inalterado).
- Mudança de UX em Consulta IA além de trocar a implementação inline pela chamada ao componente compartilhado (comportamento idêntico ao atual).

## Acceptance criteria

1. Home mostra um 5º botão, abaixo do grid de 4 cards, largura = soma das 2 colunas, texto "Cadastrar Nova Pessoa" (ou variação), estilo visualmente consistente (glass/HUD tático) mas em formato de barra — não card quadrado.
2. Clicar no botão abre um modal teleportado com todos os campos hoje presentes em "Cadastrar Pessoa" (nome, CPF com validação, data nascimento, apelido, nome da mãe, endereço, estado/cidade/bairro com autocomplete + "cadastrar novo", foto) e "SALVAR PESSOA" chamando o mesmo endpoint (`POST /pessoas/`).
3. Topo do modal exibe aviso vermelho, visualmente destacado, com frase direta (ex.: "Quer registrar uma abordagem? Use o botão Nova Abordagem") — a parte "Nova Abordagem" é um link clicável que fecha o modal e navega para a página `abordagem-nova`.
4. Consulta IA continua funcionando exatamente como hoje (busca sem resultado → botão "Cadastrar" → mesmo formulário), agora renderizado a partir do componente compartilhado — sem regressão.
5. Nova Abordagem, no bloco "Nenhuma pessoa encontrada" (ao lado de "+ Cadastrar novo abordado"), exibe aviso adicional avisando que, para cadastrar uma pessoa sem registrar abordagem, o usuário deve usar o botão "Cadastrar Nova Pessoa" da home — com link/ação que navega para lá.
6. Sem regressão nos fluxos existentes (cadastro de cidade/bairro novo, validação de CPF, upload de foto) em nenhum dos dois pontos de entrada.

## Decisions

- Formulário extraído para novo arquivo em `frontend/js/components/` (ex. `cadastro-pessoa-modal.js`), replicando o padrão de `person-photo-modal.js`.
- Modal da home é teleportado (`x-teleport="body"`), como os modais "ver mais" já existentes em `consulta.js` — evita reestruturar a árvore de componentes Alpine.
- Aviso em Nova Abordagem entra no bloco "Nenhuma pessoa encontrada" (mesmo ponto onde já existe "+ Cadastrar novo abordado"), não como banner fixo no topo do formulário inteiro — é o ponto exato onde o usuário decide qual caminho seguir, e evita chrome permanente num formulário já carregado. *(Default assumido pelo Claude; ajustável no Plan se o usuário preferir banner fixo.)*
- Texto do botão da home: "Cadastrar Nova Pessoa" — variação aceita pelo usuário, não é texto fixo.

## Risks

- Extração do formulário de `consulta.js` para componente compartilhado toca em ~130 linhas de lógica (estado + template) hoje sem cobertura automatizada — risco de regressão silenciosa no fluxo já em produção da Consulta IA. Mitigação: `slice-verification` com evidência de navegador real, comparando comportamento antes/depois da extração.
- Home page hoje não tem escopo Alpine reativo próprio (`renderHomePage` gera HTML puro; navegação via `data-navigate-to` + listener global) — abrir um modal reativo ali pode exigir dar um `x-data` local ao novo botão/modal. Detalhe de implementação a resolver no Plan/Build, não bloqueia o spec.
- Sem suíte de testes automatizados de frontend neste projeto (sem `package.json`/Jest/Playwright em `frontend/`) — verificação será manual em navegador real.

## Verification

Com `make dev` no ar, testar manualmente em navegador real (per CLAUDE.md — mudança de frontend exige teste em browser antes de reportar concluído):

- Home: botão aparece, dimensões corretas, abre modal.
- Modal: todos os campos funcionam; salvar cria pessoa de verdade (conferir via Consulta IA ou banco).
- Aviso vermelho visível; link navega pra Nova Abordagem e fecha o modal.
- Consulta IA: fluxo de busca sem resultado → Cadastrar → mesmo formulário, sem regressão.
- Nova Abordagem: bloco "Nenhuma pessoa encontrada" mostra o aviso novo; link navega pra home.
- `make lint` — garantir que nenhuma mudança de backend entrou por engano (esta é uma feature 100% frontend).
