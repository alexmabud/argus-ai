# Design: Calendário na Página de Relatórios

**Data:** 2026-04-28  
**Status:** Aprovado

## Problema

A página de Relatórios hoje exibe uma lista plana paginada de abordagens. Com o crescimento do volume de registros, a busca por um dia específico fica difícil. O objetivo é reorganizar a visualização agrupando por dia via calendário interativo.

## Solução

Substituir a lista plana por um calendário (mesmo layout/cores/fonte do calendário da página Analítico), onde o usuário seleciona o dia e vê as abordagens daquele dia.

## Abordagem Escolhida

**Opção A:** filtro `?data=YYYY-MM-DD` no endpoint existente `/abordagens/`. Reutiliza endpoints de calendário já existentes no analítico.

## Layout

```
┌─────────────────────────────┐
│  RELATÓRIO DE ABORDAGENS    │  ← header (inalterado)
│  X ABORDAGENS               │
├─────────────────────────────┤
│  🔍 Buscar por nome, placa… │  ← busca no topo (inalterada)
├─────────────────────────────┤
│  < Abril 2026 >             │  ← calendário (mesmo do analítico)
│  D  S  T  Q  Q  S  S        │
│  …  …  …  …  …  …  …        │
│        ●          ●         │  ← dots = dias com abordagem
│            [28]             │  ← hoje pré-selecionado
├─────────────────────────────┤
│  card abordagem 1           │  ← cards do dia (mesmo card atual)
│  card abordagem 2           │
│  "Nenhuma abordagem neste   │
│   dia." (se vazio)          │
└─────────────────────────────┘
```

## Comportamentos

- Entrada na página: mês atual, hoje pré-selecionado, abordagens do dia carregam automaticamente
- Troca de mês: recarrega dots, limpa seleção
- Seleção de dia: carrega abordagens do dia via API
- Busca: filtra dentro dos cards do dia selecionado (nome, placa, endereço)
- "Carregar mais" removido — um dia não justifica paginação
- Contador no header mostra quantidade do dia selecionado

## Backend

**Arquivo:** `app/api/v1/abordagens.py` + service/repository correspondente

Adicionar parâmetro opcional `data: date | None = None` ao endpoint `GET /abordagens/`:
- Com `data`: retorna abordagens do dia, sem paginação
- Sem `data`: comportamento atual inalterado (lista paginada)

Endpoints reutilizados sem mudança:
- `GET /analytics/dias-com-abordagem?mes=YYYY-MM`

## Frontend

**Arquivo:** `frontend/js/pages/ocorrencias.js`

- Adicionar estado de calendário (copiado de `dashboard.js`): `anoCalendarioAtual`, `mesCalendarioAtual`, `diaSelecionado`, `diasComAbordagem`
- Adicionar métodos: `mesMenos()`, `mesMais()`, `selecionarDia()`, `carregarDiasComAbordagem()`, `carregarAbordagensDoDia()`
- `init()` seleciona hoje e carrega em paralelo: dots do mês + abordagens do dia
- Remover `carregarMais()` e `temMais`
- Busca filtra dentro das abordagens do dia carregado
- HTML do calendário: copiar bloco de `dashboard.js` (CSS `cal-day`, `cal-led` já existe globalmente)
- Cards de abordagem, badges e estrutura visual: inalterados

## Testes

| Teste | Descrição |
|---|---|
| `test_listar_abordagens_sem_filtro_data` | Comportamento paginado original inalterado |
| `test_listar_abordagens_com_filtro_data` | Retorna só abordagens do dia informado |
| `test_listar_abordagens_data_sem_resultados` | Lista vazia para dia sem abordagens |
| `test_listar_abordagens_data_formato_invalido` | Retorna 422 |
