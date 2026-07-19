# Spec

## Problem

O modal de cadastro de pessoa ([cadastro-pessoa-modal.js](frontend/js/components/cadastro-pessoa-modal.js), compartilhado entre o botão "Cadastrar Nova Pessoa" da home e o fluxo de "Consulta IA" quando a busca não retorna resultado) não avisa o operador quando a pessoa que ele está digitando já existe no sistema.

Hoje a única barreira é um bloqueio duro por CPF: se o CPF já está cadastrado, `POST /pessoas/` retorna 409 ([pessoa_service.py:91-98](app/services/pessoa_service.py#L91-L98)), tratado como erro genérico em `erroCadastro` ([cadastro-pessoa-modal.js:404-406](frontend/js/components/cadastro-pessoa-modal.js#L404-L406)) — sem UI que mostre quem é essa pessoa. E como CPF é campo opcional no cadastro, um operador que digita só o nome (ou digita o CPF errado) não recebe nenhum aviso, mesmo que já exista alguém com nome idêntico ou muito parecido. Resultado: pessoas duplicadas no banco, quebrando o histórico de abordagens/ocorrências que deveria estar centralizado numa única ficha.

## Scope

- No modal de cadastro (`cadastro-pessoa-modal.js`), busca em tempo real (debounce) enquanto o operador digita `nome` ou `cpf`, procurando pessoas já cadastradas com nome parecido ou CPF igual.
- Reaproveita o endpoint já existente `GET /consultas/?q=...&tipo=pessoa` ([consultas.py:54-151](app/api/v1/consultas.py#L54-L151)), que já combina fuzzy match de nome (pg_trgm, `search_by_nome`) com match exato de CPF (`get_by_cpf_hash`) — sem endpoint novo no backend.
- Quando a busca encontra candidato(s), exibe um painel de aviso inline no modal, abaixo dos campos nome/CPF, listando cada candidato com o mesmo card-resumo já usado nos resultados de busca (`consulta.js`) e no preview de ficha (`pessoaPreview`, [pessoa-detalhe.js:479-520](frontend/js/pages/pessoa-detalhe.js#L479-L520)): foto, nome, apelido, CPF mascarado, data de nascimento.
- Clicar num card do aviso abre a ficha completa da pessoa existente (mesma navegação já usada em outros pontos do app, `viewPessoa(id)`).
- Aviso é **soft**: não bloqueia o cadastro. O operador pode ignorar e continuar preenchendo/salvando — a única barreira dura continua sendo o 409 de CPF exatamente igual no submit (comportamento já existente, inalterado).

## Out of scope

- Endpoint novo no backend — reaproveita `/consultas/` como está.
- Mudar a regra de bloqueio duro por CPF duplicado no submit (`POST /pessoas/` continua igual).
- Merge/unificação de pessoas duplicadas já existentes no banco (limpeza de dados histórica não faz parte desta feature).
- Detecção de duplicidade em qualquer outro formulário que não seja `cadastro-pessoa-modal.js` (ex.: cadastro de pessoa embutido no fluxo de "Nova Abordagem", que tem lógica própria de `novasPessoas` local e é intencionalmente diferente — ver [.scratch/cadastrar-nova-pessoa-home/spec.md](/.scratch/cadastrar-nova-pessoa-home/spec.md#L18)).
- Modo de edição de pessoa — confirmado que `cadastro-pessoa-modal.js` hoje é usado só para criação, não para editar pessoa existente.

## Acceptance criteria

1. Ao digitar no campo `nome` (mínimo 3 caracteres, debounce ~400ms — mesmo padrão de `consulta.js:onInput`), se existir pessoa cadastrada com nome igual ou parecido (fuzzy pg_trgm), o modal mostra um painel "Possível pessoa já cadastrada" com um card por candidato (até um limite razoável, ex. 5).
2. Ao digitar no campo `cpf` até completar um CPF válido (11 dígitos), se existir pessoa com esse CPF exato, o modal mostra o mesmo painel com o card daquela pessoa.
3. Cada card do painel mostra: foto (ou placeholder), nome, apelido, CPF mascarado, data de nascimento — mesmo layout usado em `pessoaPreview`/cards de `consulta.js`.
4. Clicar num card navega para a ficha completa daquela pessoa (reaproveitando `viewPessoa`).
5. O painel de aviso não impede submeter o formulário — o operador pode ignorar e salvar normalmente, exceto no caso de CPF exatamente igual, que continua bloqueado com 409 (comportamento já existente).
6. O aviso aparece nos dois pontos de entrada do modal (botão "Cadastrar Nova Pessoa" da home e "Cadastrar" dentro de Consulta IA), automaticamente, por ser componente compartilhado — sem lógica duplicada.
7. Sem regressão no fluxo de cadastro existente (upload de foto, endereço em cascata, validação de CPF client-side, submit).

## Decisions

- Reaproveitar `GET /consultas/?q=...&tipo=pessoa` em vez de criar endpoint dedicado — já faz fuzzy nome + exato CPF combinados, já é usado e testado no fluxo de Consulta IA. *(Default assumido pelo Claude; se o Plan encontrar limitação real — ex. limite/formatação de resposta inadequado para este uso — avalia endpoint dedicado ali.)*
- Card-resumo do painel replica o shape de dados de `PessoaRead`/`PessoaComEnderecoRead` (já retornado por `/consultas/`), sem schema novo no backend.
- Debounce/threshold do campo nome espelha o padrão já usado em `consulta.js` (400ms, resposta só dispara com o input "assentado"), para manter comportamento consistente entre buscas do app.
- Checagem de CPF só dispara com CPF completo/válido (11 dígitos) — hash HMAC não permite match parcial, então buscar com CPF incompleto não teria retorno útil.
- Aviso é sempre "soft" (não bloqueia) mesmo em match forte de nome — decisão de UX: falso positivo de nome comum (ex. "José Silva") não deve travar cadastro legítimo; a decisão final fica com o operador olhando o card-resumo.

## Risks

- `search_by_nome` (pg_trgm, threshold 0.3) pode gerar falsos positivos com nomes comuns, poluindo o painel com candidatos irrelevantes. Mitigação: threshold já calibrado em uso real (Consulta IA usa o mesmo), e o aviso é soft — não bloqueia.
- Modal de cadastro hoje não tem estado de "resultado de busca associado a um campo" — variável de estado nova (`possiveisDuplicatas`, debounce timer) precisa ser adicionada em `cadastroPessoaModal()` ([cadastro-pessoa-modal.js:183](frontend/js/components/cadastro-pessoa-modal.js#L183)) sem quebrar o restante do estado do formulário.
- Sem suíte de testes automatizados de frontend além do harness e2e recente (`frontend-e2e-coverage`) — verificação principal será manual em navegador real, per CLAUDE.md.
- Chamada de busca em tempo real (a cada tecla, mesmo com debounce) aumenta tráfego no endpoint `/consultas/` durante o preenchimento do formulário — aceitável dado o rate limit e uso já validado nesse endpoint em Consulta IA, mas vale confirmar no Verify que não há degradação perceptível.

## Verification

Com `make dev` no ar, testar manualmente em navegador real (per CLAUDE.md — mudança de frontend exige teste em browser antes de reportar concluído):

- Digitar nome de pessoa já cadastrada → painel aparece com card correto (foto, nome, apelido, CPF mascarado, nascimento).
- Digitar nome parecido (variação/apelido) → painel aparece com candidato(s) plausíveis.
- Digitar nome que não existe → painel não aparece.
- Digitar CPF completo de pessoa já cadastrada → painel aparece com aquele card.
- Digitar CPF completo novo (sem cadastro) → painel não aparece.
- Clicar num card do painel → navega para a ficha completa correta.
- Ignorar o aviso e salvar pessoa nova (nome parecido, CPF diferente) → cadastro é criado normalmente (aviso não bloqueia).
- Tentar salvar com CPF exatamente igual a um já cadastrado → continua bloqueado com erro 409 (comportamento inalterado).
- Repetir o teste do painel nos dois pontos de entrada (botão da home e Consulta IA → "Cadastrar").
- `make lint` — garantir que nenhuma mudança indevida de backend/schema entrou (esta feature deve ser majoritariamente frontend, reaproveitando endpoint existente).
