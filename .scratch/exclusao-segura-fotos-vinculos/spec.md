# Spec

## Problem

Hoje a remoção de um abordado ou veículo de uma abordagem (e de um vínculo pessoa-veículo na ficha do abordado) é um "✕" clicável direto na miniatura/card, disparando `confirm()` nativo do navegador sem nenhum passo intermediário. É fácil clicar sem querer, e o popup nativo do navegador não combina com o resto da interface. Além disso, ao auditar o código foi encontrado um buraco de permissão: `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` (desvincular veículo na ficha do abordado) não checa dono nem admin — qualquer usuário autenticado da guarnição pode remover o vínculo, diferente do padrão já aplicado em `AbordagemService` (dono da abordagem ou admin).

## Scope

1. **ABORDAGEM → Abordados**: remover o "✕" da miniatura da pessoa (`abordagem-detalhe.js`). A remoção passa a exigir abrir o modal "Foto Ampliada" (`personPhotoModal`, `frontend/js/components/person-photo-modal.js`) e clicar num ícone de lixeira discreto no canto superior direito do modal, que abre confirmação customizada antes de chamar `DELETE /abordagens/{id}/pessoas/{pessoa_id}` (permissão já correta: dono da abordagem ou admin).
2. **FICHA DO ABORDADO → Foto de Rosto/Perfil e Fotos Relacionadas ao Abordado** (`pessoa-detalhe.js`, incluindo o modal "Ver mais"): remover o "✕" `x-show="isAdmin"` da miniatura. A foto ampliada (modal local `fotoAmpliada` já existente, distinto do `personPhotoModal`) ganha o mesmo ícone de lixeira + confirmação customizada antes de chamar `DELETE /fotos/{foto_id}`. Permissão continua admin-only (sem mudança de backend/modelo).
3. **ABORDAGEM → Veículos**: hoje não existe clique para ampliar a foto do veículo nessa tela. Adicionar: (a) clique na foto/card do veículo abrindo `personPhotoModal` (já suporta seção "Dados do Veículo"/"Dados do Condutor" via parâmetro `veiculoData`, usado hoje em `pessoa-detalhe.js`); (b) remover o "✕" atual do card; (c) ícone de lixeira dentro do modal ampliado, com confirmação customizada, chamando `DELETE /abordagens/{id}/veiculos/{veiculo_id}` (permissão já correta: dono da abordagem ou admin).
4. **FICHA DO ABORDADO → Veículos Vinculados ao Abordado** (`pessoa-detalhe.js`): hoje tem um ícone de remoção direto no card (só para `v.origem === 'direto'`, sem checar dono/admin, com `confirm()` nativo). Mover a ação para dentro do `personPhotoModal` ampliado (mesmo padrão do item 3): remover o ícone do card, adicionar lixeira + confirmação customizada no modal, chamando `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}`. Apertar a permissão no backend (`PessoaVeiculoService.desvincular`) para exigir dono do vínculo (`PessoaVeiculo.criado_por_id == user.id`) ou admin/super-admin — mesmo padrão de `assert_pode_editar_abordagem` em `app/core/permissions.py`. O botão/ícone só aparece no frontend se o usuário tiver permissão.
5. **Transversal**: componente de modal de confirmação customizado e reutilizável (estilo glass-card/tema do app), com mensagem tipo "Remover [abordado/foto/veículo]? Esta ação não pode ser desfeita.", substituindo os `confirm()` nativos usados nos 4 fluxos acima. Novo componente em `frontend/js/components/`, usado por `abordagem-detalhe.js` e `pessoa-detalhe.js`.
6. `personPhotoModal` é compartilhado por outras páginas (`dashboard.js`, `consulta.js`, `pessoa-detalhe.js` para vínculos/relacionamentos) onde não faz sentido oferecer exclusão — a lixeira só aparece quando o modal é aberto num contexto de exclusão válido (abordagem atual + permissão), controlado por um parâmetro/flag explícito passado em `openPhotoModal(...)`, não por inferência de página.

## Out of scope

- Rastreio de quem fez upload de uma foto (`Foto` sem `criado_por_id`) — decisão consciente de manter a exclusão de foto admin-only, sem migration agora.
- Qualquer mudança em quem pode **adicionar** pessoa/veículo/foto — só remoção.
- Mudança visual/comportamental de outros usos do `personPhotoModal` (dashboard, consulta, relacionamentos/vínculos entre pessoas) além de ganhar o parâmetro opcional de exclusão.
- Janela de tempo ou motivo obrigatório para exclusão.

## Acceptance criteria

1. Miniatura de abordado na tela de abordagem não tem mais "✕"; clicar nela abre o modal ampliado, que mostra um ícone de lixeira (só se `podeEditar()`) no canto superior direito.
2. Clicar na lixeira do abordado abre confirmação customizada; confirmar chama `DELETE /abordagens/{id}/pessoas/{pessoa_id}` e atualiza a lista sem recarregar a página; cancelar não faz nada.
3. Miniatura de foto de rosto/evidência na ficha do abordado não tem mais "✕"; ampliar a foto mostra a lixeira só para admin; confirmar chama `DELETE /fotos/{foto_id}`.
4. Card de veículo na tela de abordagem não tem mais "✕"; clicar na foto (ou no card, se sem foto) abre o modal ampliado com dados do veículo/condutor e a lixeira (só se `podeEditar()`); confirmar chama `DELETE /abordagens/{id}/veiculos/{veiculo_id}`.
5. Card de veículo vinculado na ficha do abordado não tem mais ícone de remoção direto; ampliar a foto do veículo mostra a lixeira só se o usuário é dono do vínculo (`criado_por_id`) ou admin; confirmar chama `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}`.
6. Usuário que não é dono nem admin tentando `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` recebe 403 (hoje não recebe — qualquer autenticado da guarnição consegue).
7. Nenhum dos 4 fluxos usa mais `window.confirm()` — todos passam pelo modal de confirmação customizado.
8. `personPhotoModal` aberto a partir de dashboard/consulta/relacionamentos (sem contexto de exclusão) continua sem exibir lixeira nenhuma — comportamento inalterado.
9. Audit log continua registrando as 4 ações de remoção (já implementado nos services existentes — só validar que segue dessa forma).

## Decisions

- Confirmação: modal customizado no estilo do app (glass-card, cores do tema), não `window.confirm()`.
- Foto: permanece admin-only; sem novo campo `criado_por_id` em `Foto` nesta iteração.
- Vínculo pessoa-veículo: sobe de "qualquer usuário da guarnição" para "dono do vínculo (`criado_por_id`) ou admin/super-admin" — alinhado ao padrão de `assert_pode_editar_abordagem`; sugerir helper equivalente em `app/core/permissions.py` (ex.: `assert_pode_remover_vinculo_veiculo`) em vez de duplicar a checagem inline no service.
- `personPhotoModal` ganha um parâmetro explícito de contexto/permite-exclusão (não infere pela página) para decidir se mostra a lixeira e qual ação disparar (desvincular pessoa da abordagem vs. desvincular veículo da abordagem vs. desvincular veículo da pessoa) — evita vazar a opção de excluir para os outros usos do modal (dashboard, consulta, relacionamentos).

## Risks

- **Regressão de permissão**: apertar `PessoaVeiculoService.desvincular` pode quebrar algum fluxo hoje implícito de "qualquer um da guarnição remove" — checar se há teste existente cobrindo esse endpoint sem trava e ajustá-lo.
- **Reuso do `personPhotoModal` em 5 páginas**: precisa garantir que o novo parâmetro de exclusão só ativa nos 2 pontos de chamada corretos (abordagem-detalhe.js para pessoa e para veículo), sem afetar as demais 8+ chamadas existentes (dashboard, consulta, pessoa-detalhe para relacionamentos/vínculos).
- **Novo clique no card de veículo da abordagem** (item 3): hoje o card inteiro não tem `@click`; ao adicionar, cuidar para não conflitar com os botões "Editar"/"Adicionar foto" já presentes em cards análogos de `pessoa-detalhe.js` (usar `@click.stop` nos botões internos, se houver).
- **Dois modais de foto ampliada diferentes**: `personPhotoModal` (compartilhado) e o modal local `fotoAmpliada` de `pessoa-detalhe.js` (mais simples, sem footer) recebem a lixeira de formas ligeiramente diferentes — manter consistência visual do ícone/posição entre os dois.

## Verification

- Testes de integração no backend: `DELETE /pessoas/{pessoa_id}/veiculos/{veiculo_id}` — dono do vínculo passa, admin passa, terceiro autenticado da mesma guarnição recebe 403 (caso hoje ausente/permissivo).
- Testes (unit ou e2e) confirmando que os 3 endpoints de remoção já restritos (`.../abordagens/.../pessoas`, `.../veiculos`, `/fotos/{id}`) continuam se comportando como antes — não é para regressão.
- Teste e2e de frontend (Playwright) cobrindo os 4 fluxos: abrir foto ampliada → ver lixeira (ou não, conforme permissão) → confirmar → item some da lista; e o caso "cancelar não remove".
- Teste e2e confirmando que abrir `personPhotoModal` a partir do dashboard/consulta/relacionamentos não mostra lixeira nenhuma.
- `make test` e `make lint` verdes antes de considerar a branch pronta.
