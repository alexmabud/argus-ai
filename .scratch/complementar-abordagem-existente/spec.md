# Spec

## Problem

Numa abordagem corrida em campo, nem sempre dá tempo de cadastrar todas as pessoas presentes na hora do registro (< 40s). Hoje não há forma de voltar depois e complementar aquela mesma abordagem: cadastrar a pessoa "depois" só é possível criando uma **nova** abordagem, o que grava a localização de onde a pessoa estiver naquele momento — não o local original da ocorrência. Isso corrompe o dado geoespacial e fragmenta o registro de quem estava no mesmo evento.

## Scope

- Endpoint para vincular uma **pessoa já existente** a uma abordagem já registrada (`POST /abordagens/{id}/pessoas`).
- Endpoint para desvincular pessoa de uma abordagem (`DELETE /abordagens/{id}/pessoas/{pessoa_id}`) — necessário para corrigir adição por engano.
- Mesma coisa para **veículo** (`POST`/`DELETE /abordagens/{id}/veiculos`), reaproveitando `vincular_veiculo`/`desvincular_veiculo` já existentes no service.
- Checagem de autorização: só o `usuario_id` dono da abordagem, ou um admin da guarnição (`is_admin`/`is_super_admin`), pode chamar os endpoints acima **e** o `PATCH /abordagens/{id}` já existente. Qualquer outro usuário recebe 403.
- Frontend (`abordagem-detalhe.js`): botão "+ Adicionar abordado" na tela de detalhe, visível só para quem tem permissão. Abre autocomplete de pessoa (mesmo componente de `abordagem-nova.js`); se a pessoa não existe, opção "+ Cadastrar novo abordado" abre formulário inline/modal na própria tela, cadastra e vincula em seguida.
- Botão equivalente para adicionar veículo, reaproveitando o mesmo padrão de autocomplete de `abordagem-nova.js`.
- Ação de remover pessoa/veículo adicionado (chip com "×" ou botão remover), respeitando a mesma trava de autorização.

## Out of scope

- Reabrir edição de coordenadas/data-hora da abordagem (continuam imutáveis).
- Papel novo de "supervisor" — usa os flags de admin já existentes (`is_admin`, `is_super_admin`).
- Janela de tempo para complementar — sem prazo, vale a qualquer momento após o registro.
- Mudança de schema — `AbordagemPessoa`/`AbordagemVeiculo` já são M:N e suportam isso hoje.
- Fluxo de criação de abordagem (`abordagem-nova.js`) — só o de detalhe é alterado; o componente de autocomplete/cadastro inline é reaproveitado, não duplicado.

## Acceptance criteria

1. Dono da abordagem consegue, na tela de detalhe, adicionar uma pessoa já cadastrada e ver o vínculo refletido imediatamente (sem recarregar a página manualmente além do refresh natural do estado).
2. Dono da abordagem consegue cadastrar uma pessoa nova inline a partir da tela de detalhe e ela é vinculada automaticamente à abordagem aberta.
3. Usuário que **não** é dono nem admin recebe 403 ao tentar `POST/DELETE /abordagens/{id}/pessoas` ou `.../veiculos`, e o botão "+ Adicionar" fica oculto/desabilitado no frontend para ele.
4. Admin da guarnição (`is_admin=True` ou `is_super_admin=True`) consegue adicionar pessoa/veículo em abordagem de outro oficial da mesma guarnição.
5. `PATCH /abordagens/{id}` (observação/endereço) passa a aplicar a mesma trava — usuário não autorizado recebe 403 (hoje não há checagem nenhuma).
6. Vincular pessoa que já está vinculada (ativa) à mesma abordagem não duplica o registro — retorna erro claro (409 ou equivalente) em vez de estourar a constraint única do banco.
7. Vincular veículo segue o mesmo padrão do item 6.
8. Ação registrada em audit log (`CREATE`/`DELETE` em `abordagem_pessoa`/`abordagem_veiculo`) — já implementado no service, só validar que segue acontecendo pelos novos endpoints.
9. `AbordagemDetail` retornado por `GET /abordagens/{id}` reflete a pessoa/veículo recém-vinculado sem exigir nova query manual (o `_serializar_detalhe` já monta a partir dos relacionamentos ativos).

## Decisions

- Autorização: dono (`Abordagem.usuario_id == user.id`) OU admin da guarnição (`user.is_admin or user.is_super_admin`). Reaproveitar o padrão já usado em `app/core/permissions.py`, não criar papel novo.
- Sem prazo/expiração para complementar a abordagem.
- Escopo cobre pessoas e veículos simetricamente (o problema relatado foi de pessoas, mas o mesmo racional e o mesmo código de suporte já existem para veículo).
- Cadastro de pessoa nova abre inline/modal na tela de detalhe, replicando o padrão já usado em `abordagem-nova.js` (autocomplete + "+ Cadastrar novo abordado"), em vez de navegar para outra página.
- Reaproveitar `vincular_pessoa`/`desvincular_pessoa`/`vincular_veiculo`/`desvincular_veiculo` já existentes em `AbordagemService` (atualmente não expostos por nenhum router) — não recriar lógica equivalente.

## Risks

- **Autorização retroativa no PATCH existente**: hoje `atualizar_abordagem` não checa autoria. Adicionar a trava pode quebrar algum fluxo que hoje depende implicitamente de "qualquer um da guarnição pode editar" (não identificado no código, mas vale checar se frontend assume isso em algum lugar antes de travar).
- **Duplicidade de vínculo**: `vincular_pessoa` hoje não verifica se já existe vínculo ativo antes de inserir — pode violar o índice único `uq_abordagem_pessoa` ou (pior) criar linha nova depois de um soft-delete anterior sem reativar a antiga. Precisa tratar no service.
- **Reconciliação de relacionamento materializado**: `vincular_pessoa` já re-materializa vínculos entre pessoas via `relacionamento.registrar_vinculo` — checar que isso continua correto quando chamado repetidas vezes (idempotência) pelos novos endpoints.
- **Frontend**: reaproveitar o autocomplete de `abordagem-nova.js` em `abordagem-detalhe.js` sem duplicar componente — checar se o componente já é isolado o suficiente (arquivo `frontend/js/components/autocomplete.js`, referenciado no teste e2e existente) ou se precisa de ajuste para funcionar fora do fluxo de criação.

## Verification

- Testes de unidade/integração no service: vincular pessoa nova, vincular pessoa duplicada (erro tratado), desvincular, mesmo para veículo.
- Testes de autorização nos endpoints: dono passa, admin passa, terceiro recebe 403 — para `POST/DELETE .../pessoas`, `POST/DELETE .../veiculos` e para o `PATCH /abordagens/{id}` existente.
- Teste e2e de frontend (Playwright, seguindo o padrão de `tests/e2e/frontend/test_abordagem_nova_pessoas.py`) cobrindo: adicionar pessoa existente, cadastrar pessoa nova inline e vincular, tentar adicionar sem permissão (botão ausente/ação bloqueada).
- `make test` e `make lint` verdes antes de considerar a branch pronta.
