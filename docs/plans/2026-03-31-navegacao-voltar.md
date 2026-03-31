# Navegação Voltar — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fazer o botão "← Voltar" e o back físico do celular navegarem para a página anterior real, em vez de sempre ir para `consulta`.

**Architecture:** Adicionar um stack `navHistory` no estado global do app. `navigate()` empurra a página atual antes de trocar. Um novo método `goBack()` no app desempilha e navega (fallback: `'home'`). Um listener `popstate` captura o back físico do Android/iOS e chama `goBack()`. O `goBack()` hardcoded em `pessoa-detalhe.js` passa a delegar para o método do app.

**Tech Stack:** Alpine.js (estado reativo), Web History API (`pushState` / `popstate`), JavaScript vanilla.

---

### Task 1: Adicionar `navHistory` e `goBack()` no app + listener `popstate`

**Files:**
- Modify: `frontend/js/app.js`

**Step 1: Adicionar `navHistory: []` ao estado global**

Em `frontend/js/app.js`, na seção de estado (após `syncPending: 0`), adicionar:

```js
navHistory: [],
```

**Step 2: Atualizar `navigate()` para empurrar no stack**

Substituir o método `navigate(page)` atual:

```js
// ANTES
navigate(page) {
  this.currentPage = page;
  this.renderPage(page);
  window.history.pushState({ page }, "", `#${page}`);
  document.body.style.overflow = page === "home" ? "hidden" : "";
  window.scrollTo(0, 0);
},
```

Por:

```js
// DEPOIS
navigate(page) {
  if (this.currentPage && this.currentPage !== page) {
    this.navHistory.push(this.currentPage);
  }
  this.currentPage = page;
  this.renderPage(page);
  window.history.pushState({ page }, "", `#${page}`);
  document.body.style.overflow = page === "home" ? "hidden" : "";
  window.scrollTo(0, 0);
},
```

**Step 3: Adicionar método `goBack()` no app**

Logo após o método `navigate()`, adicionar:

```js
/**
 * Navega para a página anterior no histórico interno.
 * Fallback para 'home' se o histórico estiver vazio.
 */
goBack() {
  const prev = this.navHistory.pop() || "home";
  this.currentPage = prev;
  this.renderPage(prev);
  window.history.replaceState({ page: prev }, "", `#${prev}`);
  document.body.style.overflow = prev === "home" ? "hidden" : "";
  window.scrollTo(0, 0);
},
```

**Step 4: Adicionar listener `popstate` no `init()`**

No método `init()`, junto aos outros `window.addEventListener`, adicionar:

```js
// Capturar back físico do celular / browser
window.addEventListener("popstate", () => this.goBack());
```

**Step 5: Verificar manualmente no browser**

Abrir o app → navegar: home → consulta → pessoa-detalhe → clicar "← Voltar".
Esperado: volta para `consulta`.

Depois testar: home → pessoa-detalhe → "← Voltar".
Esperado: volta para `home`.

**Step 6: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat(nav): adicionar stack de histórico e goBack() no app"
```

---

### Task 2: Atualizar `goBack()` em `pessoa-detalhe.js` para usar o app

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:1016-1019`

**Step 1: Substituir o goBack() hardcoded**

Localizar (linha ~1016):

```js
goBack() {
  const appEl = document.querySelector("[x-data]");
  if (appEl?._x_dataStack) appEl._x_dataStack[0].navigate("consulta");
},
```

Substituir por:

```js
goBack() {
  const appEl = document.querySelector("[x-data]");
  if (appEl?._x_dataStack) appEl._x_dataStack[0].goBack();
},
```

**Step 2: Testar fluxos**

- `home → consulta → pessoa-detalhe` → "← Voltar" → deve ir para `consulta` ✓
- `home → pessoa-detalhe` (via evento de navegação direta) → "← Voltar" → deve ir para `home` ✓
- Back físico do celular em `pessoa-detalhe` → deve ir para página anterior ✓

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(nav): goBack() em pessoa-detalhe delega para app em vez de hardcode consulta"
```
