---
status: ready-for-execution
---

## Parent

.scratch/exclusao-segura-fotos-vinculos/spec.md

## What to build

Em `abordagem-detalhe.js`, o card de veículo hoje não tem nenhum clique para ampliar a foto (só o "✕" absoluto no canto do card). Adicionar `@click` no card/foto do veículo abrindo `personPhotoModal` já usado para pessoas — ele já suporta a seção "Dados do Veículo"/"Dados do Condutor" via parâmetro `veiculoData` (usado hoje em `pessoa-detalhe.js`). Remover o "✕" atual do card.

Reaproveitar o `deleteContext` introduzido na issue 03: para veículo de abordagem, algo como `{ tipo: 'veiculo-abordagem', abordagemId, veiculoId }`. Quando presente e `podeEditar()` for verdadeiro, mostra a lixeira no modal ampliado (mesmo componente de confirmação da issue 02). Confirmar chama `DELETE /abordagens/{id}/veiculos/{veiculo_id}` e atualiza `ab.veiculos` localmente.

Cuidado: o card de veículo pode ter outros elementos clicáveis futuramente (hoje não tem, mas ao adicionar o `@click` no card, garantir que não conflita com nada dentro dele).

## Acceptance criteria

- [ ] Card de veículo na tela de abordagem não tem mais "✕".
- [ ] Clicar na foto do veículo (ou no card, se não houver foto) abre o modal ampliado mostrando placa/modelo/cor/ano e dados do condutor vinculado, se houver.
- [ ] Lixeira aparece no modal só se `podeEditar()` for verdadeiro.
- [ ] Confirmar remoção chama `DELETE /abordagens/{id}/veiculos/{veiculo_id}`, remove o veículo de `ab.veiculos` no estado local e fecha o modal.
- [ ] Usuário sem permissão não vê a lixeira ao abrir o modal do veículo.

## Blocked by

03-fluxo-remover-abordado-da-abordagem (reaproveita o `deleteContext` e o wiring de lixeira/confirmação estabelecidos ali).

## Verification

Teste e2e Playwright cobrindo: abrir foto ampliada do veículo, dono/admin remove com confirmação, terceiro não vê a lixeira. `make test` verde.
