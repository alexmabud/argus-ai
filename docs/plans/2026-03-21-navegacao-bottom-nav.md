# Nova Navegação — Bottom Nav Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir a sidebar lateral por um bottom navigation bar + header reformulado, mantendo comportamento idêntico em browser e PWA mobile.

**Architecture:** Remove completamente a sidebar e seu componente Alpine.js. O header ganha botão voltar (visível fora da home), LEDs de status e avatar do usuário. Um bottom nav fixo aparece apenas em subpáginas, com 5 botões e efeito glassmorphism.

**Tech Stack:** HTML, CSS (custom properties + glassmorphism), Alpine.js (x-show, x-bind), sem dependências novas.

---

### Task 1: Remover estilos da sidebar do CSS

**Files:**
- Modify: `frontend/css/app.css` (linhas 40-46, 408-656, 967-1018)

Não há testes automatizados para CSS — verificação é visual no browser. Abra `http://localhost:8000` antes e depois de cada task para comparar.

**Step 1: Remover variáveis CSS da sidebar**

No bloco `:root` (linha ~41), remover as duas linhas:
```css
/* REMOVER: */
  --sidebar-width:     240px;
  --sidebar-collapsed:  64px;
```

**Step 2: Remover bloco SIDEBAR completo (linhas ~408–656)**

Remover tudo entre os comentários `/* SIDEBAR */` e `/* MAIN CONTENT AREA */`, mantendo apenas o novo `.app-main`:

```css
/* ========================================
   MAIN CONTENT AREA
   ======================================== */
.app-main {
  margin-top: var(--header-height);
  min-height: calc(100vh - var(--header-height));
  padding: 20px;
  position: relative;
  z-index: 2;
}

.app-main.has-bottom-nav {
  padding-bottom: 80px;
}

@media (max-width: 768px) {
  .app-main {
    padding: 16px;
  }
  .app-main.has-bottom-nav {
    padding-bottom: 80px;
  }
}
```

**Step 3: Remover estilos `.hamburger-btn` e `.sidebar-toggle` (linhas ~964–1018)**

Remover os dois blocos completos:
- `/* HAMBURGER MENU BUTTON */` (linhas ~964–991)
- `/* SIDEBAR TOGGLE (DESKTOP) */` (linhas ~993–1018)

**Step 4: No bloco `@media (max-width: 768px)` restante (linha ~987–991), remover as linhas de sidebar:**
```css
/* REMOVER estas linhas do media query mobile: */
.header-info { display: none; }
.header-search { display: none; }
```
O media query `@media (max-width: 768px) { .app-main { padding: 16px; } }` permanece.

**Step 5: Commit**
```bash
git add frontend/css/app.css
git commit -m "refactor(frontend): remover estilos da sidebar do CSS"
```

---

### Task 2: Adicionar estilos do novo Header e Bottom Nav no CSS

**Files:**
- Modify: `frontend/css/app.css` (append ao final, antes do bloco SCROLLBAR)

**Step 1: Adicionar estilos do botão voltar no header**

Inserir após o bloco `.header-clock` (linha ~398):

```css
/* ========================================
   HEADER — BACK BUTTON
   ======================================== */
.header-back-btn {
  display: flex;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition);
  flex-shrink: 0;
}

.header-back-btn:hover {
  color: var(--color-primary);
  border-color: rgba(0, 212, 255, 0.3);
}

/* ========================================
   HEADER — STATUS LEDS
   ======================================== */
.header-status-leds {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-status-led {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-data);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
}

/* ========================================
   HEADER — USER AVATAR
   ======================================== */
.header-user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  color: var(--color-primary);
  flex-shrink: 0;
  overflow: hidden;
  cursor: pointer;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.header-user-avatar:hover {
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.2);
}

.header-user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

**Step 2: Adicionar estilos do Bottom Nav**

Inserir antes do bloco `/* SCROLLBAR CUSTOM */`:

```css
/* ========================================
   BOTTOM NAVIGATION BAR
   ======================================== */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: rgba(5, 10, 15, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid rgba(0, 212, 255, 0.12);
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0 8px;
  z-index: 150;
}

.bottom-nav-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: transform var(--transition), color var(--transition);
  padding: 0;
  -webkit-tap-highlight-color: transparent;
}

.bottom-nav-btn:hover {
  transform: scale(1.08);
  color: var(--color-text);
}

.bottom-nav-btn.active {
  color: var(--color-primary);
  filter: drop-shadow(0 0 6px rgba(0, 212, 255, 0.6));
}

.bottom-nav-btn svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.bottom-nav-label {
  font-family: var(--font-data);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  line-height: 1;
}
```

**Step 3: Commit**
```bash
git add frontend/css/app.css
git commit -m "feat(frontend): adicionar estilos bottom nav e header reformulado"
```

---

### Task 3: Reformular o HTML do header e remover sidebar no index.html

**Files:**
- Modify: `frontend/index.html`

**Step 1: Substituir o bloco `<header>` completo (linhas ~78–120)**

Substituir o `<header class="app-header" ...>` atual por:

```html
<!-- Header -->
<header class="app-header">
  <!-- Botão Voltar (só fora da home) -->
  <button class="header-back-btn"
          x-show="currentPage !== 'home'"
          x-cloak
          @click="navigate('home')"
          title="Voltar">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
  </button>

  <!-- Logo -->
  <span class="header-logo" @click="navigate('home')">ARGUS</span>

  <!-- Search bar -->
  <div class="header-search" x-data="{ searchQuery: '' }">
    <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
    <input type="text"
           x-model="searchQuery"
           placeholder="CONSULTAR BASE OPERACIONAL..."
           @keydown.enter.prevent="if(searchQuery.trim()) { navigate('consulta'); }">
  </div>

  <!-- Spacer -->
  <div style="flex:1"></div>

  <!-- LEDs de status -->
  <div class="header-status-leds">
    <div class="header-status-led">
      <span class="status-dot" :class="online ? 'status-dot-online' : 'status-dot-offline'"></span>
      <span>API</span>
    </div>
    <div class="header-status-led">
      <span class="status-dot status-dot-online"></span>
      <span>IA</span>
    </div>
    <div class="header-status-led">
      <span class="status-dot status-dot-sync"></span>
      <span>DB</span>
    </div>
  </div>

  <!-- Avatar do usuário -->
  <div class="header-user-avatar" @click="navigate('perfil')" title="Perfil">
    <template x-if="user?.foto_url">
      <img :src="user.foto_url" :alt="user.nome" />
    </template>
    <template x-if="!user?.foto_url">
      <span x-text="user?.nome ? user.nome.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase() : '?'"></span>
    </template>
  </div>
</header>
```

**Step 2: Substituir o bloco do wrapper da sidebar (linhas ~122–200)**

Remover o `<div x-data="sidebarComponent()" ...>` com tudo dentro (overlay, aside, e o `<main>`).

Substituir por estrutura simples:

```html
<!-- Main content -->
<main class="app-main" :class="{ 'has-bottom-nav': currentPage !== 'home' }">
  <div id="page-content"></div>
</main>

<!-- Bottom Navigation (só fora da home) -->
<nav class="bottom-nav" x-show="currentPage !== 'home'" x-cloak>
  <button class="bottom-nav-btn" :class="{ active: currentPage === 'abordagem-nova' }" @click="navigate('abordagem-nova')">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>
    <span class="bottom-nav-label">Abordagem</span>
  </button>

  <button class="bottom-nav-btn" :class="{ active: currentPage === 'consulta' }" @click="navigate('consulta')">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
    <span class="bottom-nav-label">Consulta IA</span>
  </button>

  <button class="bottom-nav-btn" :class="{ active: currentPage === 'home' }" @click="navigate('home')">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
    <span class="bottom-nav-label">Início</span>
  </button>

  <button class="bottom-nav-btn" :class="{ active: currentPage === 'ocorrencia-upload' }" @click="navigate('ocorrencia-upload')">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M12 12v6"/><path d="m15 15-3-3-3 3"/></svg>
    <span class="bottom-nav-label">Ocorrência</span>
  </button>

  <button class="bottom-nav-btn" :class="{ active: currentPage === 'dashboard' }" @click="navigate('dashboard')">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
    <span class="bottom-nav-label">Analítico</span>
  </button>
</nav>
```

**Step 3: Remover o script da sidebar no final do index.html**

Remover a linha:
```html
<script src="/js/components/sidebar.js?v=4"></script>
```

**Step 4: Verificar visualmente**

Abrir `http://localhost:8000` no browser:
- Home: header com logo + search + LEDs + avatar. Sem botão voltar. Sem bottom nav.
- Clicar em "Nova Abordagem": botão voltar aparece, bottom nav aparece na base.
- Clicar "Início" no bottom nav: volta para home, bottom nav some.
- Clicar no avatar: vai para perfil.

**Step 5: Commit**
```bash
git add frontend/index.html
git commit -m "feat(frontend): reformular header e adicionar bottom nav"
```

---

### Task 4: Limpar app.js — remover referências à sidebar

**Files:**
- Modify: `frontend/js/app.js`

**Step 1: Verificar se há referências diretas ao sidebarComponent**

O `app.js` atual não importa `sidebarComponent` diretamente — o Alpine.js inicializa via `x-data` no HTML. Porém, o método `navigate()` pode ter lógica de fechar sidebar mobile.

Checar no `app.js` se existe qualquer chamada a `closeMobile`, `mobileOpen`, ou `sidebar`. Se existir, remover.

Verificar também que o `navigate()` em `app.js` não precisa mais disparar `sidebar:toggle-mobile`.

**Step 2: Remover o arquivo sidebar.js**

```bash
git rm frontend/js/components/sidebar.js
```

**Step 3: Commit**
```bash
git add frontend/js/app.js
git commit -m "refactor(frontend): remover sidebarComponent e arquivo sidebar.js"
```

---

### Task 5: Ajuste no header — responsividade e clock

**Files:**
- Modify: `frontend/css/app.css`
- Modify: `frontend/index.html`

**Contexto:** O header atual tem um `header-clock` e informações de matrícula/guarnição. Com o novo layout, o relógio e esses dados ficam sem espaço visual adequado. Decisão: remover o relógio e os campos OP/GU do header (já redundantes — o perfil tem essas infos). Manter apenas: voltar + logo + search + LEDs + avatar.

**Step 1: Remover do HTML do header os elementos `header-info` e `header-clock`**

O novo header (criado na Task 3) já não inclui esses elementos. Verificar que o HTML não tem sobras de `header-clock`, `header-info-item`, `header-info`.

**Step 2: Remover estilos `.header-info`, `.header-info-item`, `.header-clock` do CSS (linhas ~369–406)**

```css
/* REMOVER os três blocos: */
.header-info { ... }
.header-info-item { ... }
.header-info-item .label { ... }
.header-info-item .value { ... }
.header-clock { ... }
```

**Step 3: Ajustar media query mobile no header**

No bloco `@media (max-width: 768px)`, o `.header-search` foi removido da regra anterior. Adicionar de volta a regra para ocultar search no mobile (tela pequena):

```css
@media (max-width: 480px) {
  .header-search {
    display: none;
  }
}
```

Isso mantém a search bar em tablets mas some em phones pequenos.

**Step 4: Verificar no mobile (DevTools → iPhone)**

- Header deve mostrar: [← voltar] [ARGUS] [espaço] [LEDs] [avatar]
- Em telas < 480px: search some, LEDs e avatar permanecem

**Step 5: Commit**
```bash
git add frontend/css/app.css frontend/index.html
git commit -m "refactor(frontend): limpar header-info e ajustar responsividade"
```

---

### Task 6: Incrementar versões de cache dos assets

**Files:**
- Modify: `frontend/index.html`

**Contexto:** O PWA usa query strings (`?v=N`) para forçar reload dos assets após mudanças. Após alterar `app.css` e `app.js`, incrementar as versões.

**Step 1: Atualizar versões no index.html**

```html
<!-- De: -->
<link rel="stylesheet" href="/css/app.css?v=5">
<!-- Para: -->
<link rel="stylesheet" href="/css/app.css?v=6">

<!-- De: -->
<script src="/js/app.js?v=5"></script>
<!-- Para: -->
<script src="/js/app.js?v=6"></script>
```

**Step 2: Commit final**
```bash
git add frontend/index.html
git commit -m "chore(frontend): incrementar versão de cache após refactor de navegação"
```

---

## Verificação Final

Após todas as tasks:

1. **Home:** header limpo, sem botão voltar, sem bottom nav, cards de ação visíveis
2. **Subpágina (ex: abordagem-nova):** botão voltar no header, bottom nav na base com botão "Abordagem" ativo em cyan
3. **Avatar no header:** clica → vai para perfil
4. **LEDs:** três dots API · IA · DB visíveis no header
5. **Voltar pelo bottom nav:** clica "Início" → home, bottom nav some
6. **Mobile (DevTools iPhone):** layout igual ao desktop, bottom nav com área de toque confortável (64px)
7. **Sem referências à sidebar** no código (verificar com `grep -r "sidebar" frontend/`)
