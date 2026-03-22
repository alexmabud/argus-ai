# Calendário Analítico — Refactor Visual e Fix Hover

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir o bug de hover preto no calendário e melhorar o layout com células quadradas e LED azul nos dias com abordagem.

**Architecture:** Substituir manipulação direta de DOM (`@mouseover`/`@mouseout` + `$el.style`) por classes CSS reativas via `:class` binding do Alpine.js. O hover fica 100% no CSS nativo, eliminando o conflito com `:style` reativo.

**Tech Stack:** Alpine.js, CSS custom properties (var(--color-*)), HTML inline em JS (dashboard.js)

---

### Task 1: Adicionar bloco `<style>` com classes do calendário no template

**Files:**
- Modify: `frontend/js/pages/dashboard.js` — função `renderDashboard()`, logo após a abertura do template string (linha ~9, antes do primeiro `<div`)

**Contexto:** O arquivo `renderDashboard()` retorna uma template string com HTML. Adicione um bloco `<style>` no início do template (antes do `<div x-data=...>`). Isso é prática comum em componentes JS que geram HTML.

**Step 1: Adicionar o bloco `<style>` no início do template**

Localize a linha:
```js
  return `
    <div x-data="dashboardPage()" x-init="load()" ...>
```

Adicione logo após o `` return ` `` e antes do `<div x-data`:

```html
    <style>
      .cal-day {
        position: relative;
        font-family: var(--font-data);
        font-size: 13px;
        font-weight: 500;
        aspect-ratio: 1;
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border: 1px solid transparent;
        background: transparent;
        transition: background 150ms, border-color 150ms, color 150ms;
        color: var(--color-text-muted);
        width: 100%;
      }
      .cal-day:hover {
        background: rgba(0, 212, 255, 0.06);
        border-color: rgba(0, 212, 255, 0.2);
        color: var(--color-text);
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
      .cal-day.is-hoje .cal-day-num {
        color: var(--color-primary);
        text-decoration: underline;
        text-underline-offset: 3px;
      }
      .cal-led {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--color-primary);
        box-shadow: 0 0 6px var(--color-primary);
        margin-top: 3px;
        flex-shrink: 0;
      }
    </style>
```

**Step 2: Verificar visualmente no browser**

Abrir `http://localhost:8000/#dashboard` e confirmar que os estilos base do calendário não quebraram (células ainda aparecem).

**Step 3: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(frontend): adicionar classes CSS para calendário analítico"
```

---

### Task 2: Substituir o `<button>` do dia no grid do calendário

**Files:**
- Modify: `frontend/js/pages/dashboard.js` — trecho entre `<!-- Grid de dias -->` e `</template>` (linhas ~143–161)

**Contexto:** O botão atual usa `:style` reativo + `@mouseover`/`@mouseout` inline — essa combinação causa o bug. Substituir completamente pelo padrão com `:class`.

**Step 1: Localizar o trecho a substituir**

O trecho atual é:
```html
<button
  style="position:relative;font-family:var(--font-data);font-size:12px;font-weight:500;padding:4px 0;border-radius:4px;display:flex;flex-direction:column;align-items:center;cursor:pointer;border:1px solid transparent;background:transparent;transition:all 150ms;"
  :style="isDiaSelecionado(dia)
    ? 'background:rgba(0,212,255,0.15);border-color:rgba(0,212,255,0.4);color:var(--color-primary);font-weight:700;box-shadow:0 0 8px rgba(0,212,255,0.15);'
    : 'color:var(--color-text-muted);'"
  @click="selecionarDia(dia)"
  @mouseover="if(!isDiaSelecionado(dia)) $el.style.background='var(--color-surface-hover)'"
  @mouseout="if(!isDiaSelecionado(dia)) $el.style.background='transparent'">
  <span x-text="dia"></span>
  <span x-show="diaTemAbordagem(dia)"
        style="width:4px;height:4px;border-radius:50%;background:var(--color-primary);margin-top:2px;box-shadow:0 0 4px var(--color-primary);">
  </span>
</button>
```

**Step 2: Substituir pelo novo padrão**

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

**Step 3: Verificar no browser**

- Hover nas células: não devem ficar pretas
- Clicar num dia: estilo selecionado deve aparecer
- Dia atual: número deve aparecer em ciano com sublinhado
- Dias com abordagem: LED azul deve aparecer abaixo do número

**Step 4: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "fix(frontend): corrigir hover preto no calendário usando classes CSS"
```

---

### Task 3: Adicionar método `diaEHoje` no componente Alpine

**Files:**
- Modify: `frontend/js/pages/dashboard.js` — objeto retornado por `dashboardPage()`, junto dos outros métodos do calendário (~linha 286)

**Contexto:** O método `isDiaSelecionado` já existe. Adicionar `diaEHoje` logo abaixo dele.

**Step 1: Localizar o método `isDiaSelecionado`**

```js
isDiaSelecionado(dia) {
  return (
    this.diaSelecionado === dia &&
    this._mesSelec === this.mesCalendarioAtual &&
    this._anoSelec === this.anoCalendarioAtual
  );
},
```

**Step 2: Adicionar `diaEHoje` logo após**

```js
diaEHoje(dia) {
  return (
    dia === this.diaHoje &&
    this.mesCalendarioAtual === this.mesHoje &&
    this.anoCalendarioAtual === this.anoHoje
  );
},
```

**Step 3: Verificar no browser**

Navegar ao mês atual: o dia de hoje (22 de março de 2026) deve ter o número em ciano com sublinhado.
Navegar a outro mês: nenhum dia deve ter o estilo `is-hoje`.

**Step 4: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(frontend): destacar dia atual no calendário analítico"
```

---

### Task 4: Verificação final

**Step 1: Testar todos os estados visuais**

Checar no browser:
- [ ] Hover em dia sem abordagem → fundo azul sutil, borda discreta, sem preto
- [ ] Hover em dia selecionado → fundo levemente mais intenso, não reseta
- [ ] Dia com abordagem → LED azul com glow visível abaixo do número
- [ ] Dia selecionado → fundo ciano, borda ciano, glow
- [ ] Dia atual → número ciano + sublinhado
- [ ] Navegar meses → `is-hoje` some ao sair do mês atual
- [ ] Clicar dia → lista de pessoas aparece abaixo

**Step 2: Lint**

```bash
make lint
```

Expected: sem erros novos.
