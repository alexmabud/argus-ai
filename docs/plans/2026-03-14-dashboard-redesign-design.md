# Dashboard Redesign — Design Document

**Data:** 2026-03-14
**Status:** Aprovado

## Visão Geral

Redesign completo do dashboard analítico. Layout único scrollável (mobile-first), substituindo os 4 cards atuais por uma estrutura mais rica com métricas por período, gráficos de linha dupla, calendário interativo e lista de recorrentes com foto.

CPF exibido completo — acesso restrito a policiais autenticados.

---

## Seção 1: Cards de Resumo

Três blocos empilhados, cada um com label de período e grid 2×1 de métricas:

- **Hoje** — abordagens do dia + pessoas abordadas hoje
- **Este Mês** — abordagens do mês corrente + pessoas abordadas no mês
- **Total** — abordagens de todos os tempos + pessoas distintas totais

Números grandes: azul para abordagens, verde para pessoas. O número de pessoas sempre será ≥ número de abordagens (cada abordagem tem ao menos 1 pessoa).

### Endpoints novos
- `GET /analytics/resumo-hoje` → `{ abordagens, pessoas }`
- `GET /analytics/resumo-mes` → `{ abordagens, pessoas }`
- `GET /analytics/resumo-total` → `{ abordagens, pessoas }`

---

## Seção 2: Gráficos ApexCharts

ApexCharts carregado via CDN em `index.html`. Tema escuro. Dois cards empilhados:

### Gráfico 1 — Abordagens por Dia (últimos 30 dias)
- Linha azul: total de abordagens por dia
- Linha verde: total de pessoas abordadas por dia
- Eixo X: datas (`DD/MM`)
- Tooltip com os dois valores

### Gráfico 2 — Abordagens por Mês (últimos 12 meses)
- Mesmas duas séries, eixo X: `MMM/AA`

### Endpoints novos
- `GET /analytics/por-dia?dias=30` → `[{ data: "2026-03-14", abordagens, pessoas }]`
- `GET /analytics/por-mes?meses=12` → `[{ mes: "2026-03", abordagens, pessoas }]`

---

## Seção 3: Calendário + Pessoas do Dia

Um card único com duas partes:

### Calendário mini
- Grid 7 colunas (dom → sáb), mês atual
- Navegação `< / >` para mês anterior/próximo
- Dias com abordagem: ponto azul abaixo do número
- Dia selecionado: fundo azul destacado
- Default: hoje

### Lista de pessoas do dia selecionado
- Itens: foto 32×32 (`foto_principal_url` ou placeholder) + nome completo + CPF
- Click → navega para `pessoa-detalhe`
- Vazio: "Nenhuma abordagem neste dia"

### Endpoints novos
- `GET /analytics/dias-com-abordagem?mes=2026-03` → `[14, 15, 20]` (lista de dias com abordagem)
- `GET /analytics/pessoas-do-dia?data=2026-03-14` → `[{ id, nome, cpf, foto_url }]`

---

## Seção 4: Pessoas Recorrentes

Card final com top 10 pessoas mais abordadas (all-time da guarnição):

- Foto 32×32 + nome completo + CPF + contador `Nx` em destaque
- Ordenado por total de abordagens (maior → menor)
- Click → navega para `pessoa-detalhe`

### Alteração em endpoint existente
- `GET /analytics/pessoas-recorrentes?limit=10` — já existe; adicionar `foto_url` e `cpf` no retorno do `AnalyticsService`

---

## Arquitetura Frontend

- Alpine.js com `dashboardPage()` refatorado
- ApexCharts via CDN (tema escuro, responsivo)
- Calendário mini implementado em Alpine.js puro (sem lib externa)
- Todas as chamadas em `Promise.all` no `load()`; calendário faz chamadas adicionais ao mudar mês ou selecionar dia

## Arquitetura Backend

Todos os endpoints novos em `app/api/v1/analytics.py` + `app/services/analytics_service.py`. Seguem o padrão existente: filtro `guarnicao_id`, `Abordagem.ativo`, async.

---

## Fora de Escopo

- Gráfico de horários de pico (removido do novo layout)
- Mascaramento de CPF (não necessário — acesso restrito a policiais)
- Mapa de calor (existe mas não está no dashboard principal)
