# Design: Calendário Analítico — Refactor Visual e Fix Hover

**Data:** 2026-03-22
**Escopo:** `frontend/js/pages/dashboard.js` — seção calendário

## Problema

O calendário da página Analítico apresenta dois bugs:

1. **Hover preto:** `@mouseover`/`@mouseout` manipulam `$el.style.background` diretamente, conflitando com o binding reativo `:style` do Alpine.js. Resultado: células ficam com fundo escuro (#1A2940) e não resetam corretamente.
2. **LED azul não visível:** o `<span>` do indicador existe mas é obscurecido pelo conflito de estilos acima.

## Solução — Opção 1: CSS classes reativas

Substituir toda a lógica de estilo inline + manipulação direta por:

- Um bloco `<style>` injetado no topo do template com classes CSS dedicadas ao calendário
- `:class` binding do Alpine para aplicar as classes condicionalmente
- Hover 100% via CSS (`:hover` nativo), sem JS

## Design das classes CSS

```css
.cal-day {
  position: relative;
  font-family: var(--font-data);
  font-size: 13px;
  font-weight: 500;
  padding: 0;
  aspect-ratio: 1;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 1px solid transparent;
  background: transparent;
  transition: all 150ms;
  color: var(--color-text-muted);
}

.cal-day:hover {
  background: rgba(0, 212, 255, 0.06);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--color-text);
}

.cal-day.is-hoje .cal-day-num {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.cal-day.is-selecionado {
  background: rgba(0, 212, 255, 0.15);
  border-color: rgba(0, 212, 255, 0.4);
  color: var(--color-primary);
  font-weight: 700;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.15);
}

.cal-day.is-selecionado:hover {
  background: rgba(0, 212, 255, 0.2);
}

.cal-led {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 6px var(--color-primary);
  margin-top: 3px;
}
```

## Estrutura do botão do dia

```html
<button
  class="cal-day"
  :class="{
    'is-selecionado': isDiaSelecionado(dia),
    'is-hoje': diaEHoje(dia)
  }"
  @click="selecionarDia(dia)">
  <span class="cal-day-num" x-text="dia"></span>
  <span class="cal-led" x-show="diaTemAbordagem(dia)"></span>
</button>
```

## Método novo — diaEHoje(dia)

```js
diaEHoje(dia) {
  return (
    dia === this.diaHoje &&
    this.mesCalendarioAtual === this.mesHoje &&
    this.anoCalendarioAtual === this.anoHoje
  );
}
```

## Arquivos afetados

- `frontend/js/pages/dashboard.js` — template HTML do calendário + método `diaEHoje`

## Critérios de sucesso

- Hover não deixa células pretas
- LED azul aparece nos dias com abordagem
- Dia atual visualmente destacado
- Dia selecionado mantém estilo ao passar o mouse
