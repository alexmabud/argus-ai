# Manual em imagens — Argus AI

Imagens do passo a passo de **Nova Abordagem** e **Consulta por IA**, renderizadas
com o layout real do sistema (mesmo CSS e componentes do frontend) e dados fictícios.

## Conteúdo (`imagens/`)

### Nova Abordagem
- `abordagem_poster.png` — visão geral anotada (balões ①–⑤ + legenda)
- `abordagem_passo1_buscar.png` — buscar o abordado por nome/CPF
- `abordagem_passo2_cadastrar.png` — cadastrar novo abordado
- `abordagem_passo3_foto_gps.png` — abordado + foto do rosto + GPS automático
- `abordagem_passo4_veiculo.png` — veículo e vínculo (quem estava no carro)
- `abordagem_passo5_observacao.png` — observação por texto/voz + registrar
- `abordagem_passo6_sucesso.png` — confirmação

### Consulta por IA
- `consulta_poster.png` — visão geral anotada (balões ①–③ + ★)
- `consulta_passo1_nome_cpf.png` — busca por nome/CPF
- `consulta_passo2_facial.png` — reconhecimento facial (% de semelhança)
- `consulta_passo3_endereco.png` — filtro por endereço
- `consulta_passo4_veiculo.png` — busca por veículo

## Como regenerar
As imagens são geradas por `build.mjs` (Playwright/Chromium headless) a partir de
`frontend/css/app.css`. Não fazem parte do app — são material de treinamento/manual.
