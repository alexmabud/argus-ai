# Design — Mapa de Abordagens no Analítico

**Data:** 2026-03-28
**Status:** Aprovado

## Contexto

A página analítica já exibe um calendário interativo onde o operador seleciona um dia e vê a lista de pessoas abordadas naquele dia. A ficha individual de cada pessoa já possui um mapa Leaflet com marcadores/calor de todas as abordagens dela.

O objetivo é adicionar um mapa no analítico mostrando os pontos geográficos de **todas as abordagens do dia selecionado**, junto com a lista de pessoas já existente.

## Decisões de Design

- **Endpoint dedicado** (`GET /analytics/abordagens-do-dia?data=YYYY-MM-DD`) — separação de responsabilidades, reutilizável, chamado em paralelo com `pessoas-do-dia` via `Promise.all`.
- **Sem dados de localização**: exibir bloco com mensagem "Sem dados de localização para este dia" (não ocultar).
- **Popup**: apenas horário da abordagem (sem link para ficha — evolução futura).
- **Modos**: Marcadores (MarkerCluster) + Calor (HeatLayer) — padrão já estabelecido no projeto.

## Backend

### Novo endpoint

```
GET /api/v1/analytics/abordagens-do-dia?data=YYYY-MM-DD
```

**Resposta:**
```json
[
  {"lat": -23.5505, "lng": -46.6333, "horario": "14:32"},
  {"lat": -23.5510, "lng": -46.6340, "horario": "15:10"}
]
```

### Service — `analytics_service.py`

Novo método `abordagens_do_dia(guarnicao_id, data)`:
- Join: `Abordagem` filtrado por `guarnicao_id`, `ativo`, `func.date(data_hora) == data_obj`
- Filtro: `latitude IS NOT NULL AND longitude IS NOT NULL`
- Retorno: lista de `{lat, lng, horario}` — horario em `HH:MM` (horário local)

### Router — `analytics.py`

Novo handler `abordagens_do_dia` anotado com `@router.get("/abordagens-do-dia")`, docstring Google Style PT-BR.

## Frontend

### Estado novo em `dashboard.js`

```js
pontosMapaDia: [],
mapaAnaliticoInst: null,
_mapaAnaliticoObserver: null,
modoMapaAnalitico: 'marcadores',
clusterAnalitico: null,
heatAnalitico: null,
```

### Fluxo ao selecionar dia

`selecionarDia(dia)` passa a usar `Promise.all`:
```js
await Promise.all([
  this.carregarPessoasDoDia(dataStr),
  this.carregarPontosMapaDia(dataStr),
]);
```

Antes de carregar, destrói instância anterior do mapa:
```js
this.destroyMapaAnalitico();
```

### Novos métodos

- `carregarPontosMapaDia(data)` — chama `/analytics/abordagens-do-dia?data=...`
- `initMapaAnalitico()` — cria mapa Leaflet, MarkerCluster e HeatLayer (padrão de `pessoa-detalhe.js`)
- `destroyMapaAnalitico()` — remove instância e observer (chamado ao trocar mês e ao selecionar novo dia)
- `toggleModoMapaAnalitico(modo)` — alterna entre marcadores e calor

### HTML — bloco abaixo da lista de pessoas

```html
<!-- Mapa de Abordagens do Dia -->
<div x-show="diaSelecionado !== null && !loadingPessoas" ...>
  <h3>Localização das Abordagens</h3>

  <!-- Sem dados -->
  <div x-show="pontosMapaDia.length === 0">
    Sem dados de localização para este dia.
  </div>

  <!-- Mapa -->
  <div x-show="pontosMapaDia.length > 0">
    <!-- botões Marcadores / Calor -->
    <div id="mapa-analitico-dia" style="height: 280px; ..."></div>
  </div>
</div>
```

IntersectionObserver inicia o mapa apenas quando o div entra na viewport (mesmo padrão de `pessoa-detalhe.js`).

## Fora do Escopo

- Clicar no marcador para abrir ficha da pessoa
- Filtro por período (não é por dia, já existe o heat map de 30 dias separado)
- Alterações nos endpoints existentes

## Arquivos Afetados

| Arquivo | Mudança |
|---|---|
| `app/services/analytics_service.py` | Novo método `abordagens_do_dia` |
| `app/api/v1/analytics.py` | Novo handler `GET /abordagens-do-dia` |
| `frontend/js/pages/dashboard.js` | Estado, métodos e HTML do mapa |
