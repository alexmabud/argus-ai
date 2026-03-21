# Bottom Nav "Tactical Pulse" Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesenhar visualmente os 5 botões do bottom navigation com pill estruturado, glow neon e barra indicadora animada.

**Architecture:** Dois arquivos: `app.css` recebe os novos estilos (`.nav-pill`, `.nav-indicator`, sobrescritas de `.bottom-nav-btn`) e `index.html` recebe a estrutura HTML interna da pill em cada botão. Sem dependências novas. Sem JS.

**Tech Stack:** CSS puro (vars já existentes), HTML, design system cyberpunk existente (variáveis `--color-primary`, `--color-text-dim`, animação `pulse-glow` já definida).

---

## Task 1: Atualizar CSS do bottom nav em `app.css`

**Files:**
- Modify: `frontend/css/app.css` (linhas 783–841, seção `BOTTOM NAVIGATION BAR`)

**Contexto das variáveis disponíveis:**
- `--color-primary` = `#00D4FF` (ciano)
- `--color-text-muted` = `#6B8FA8`
- `--color-text-dim` = `#3A5068`
- `--transition` = `150ms ease`
- `pulse-glow` = keyframe já existente no CSS (linhas 189–192)
- `--font-data` = `'Rajdhani', sans-serif`

**Step 1: Substituir o bloco inteiro da seção BOTTOM NAVIGATION BAR**

Localizar o bloco atual (aprox. linhas 783–841) e substituir por:

```css
/* ========================================
   BOTTOM NAVIGATION BAR
   ======================================== */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 68px;
  background: rgba(5, 10, 15, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid rgba(0, 212, 255, 0.12);
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0 4px;
  z-index: 150;
}

.bottom-nav-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
  transition: all 200ms ease;
}

/* Pill — wrapper interno de cada botão */
.nav-pill {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 14px 6px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  transition: all 200ms ease;
}

/* Barra indicadora no topo da pill */
.nav-indicator {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 32px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 0 0 2px 2px;
  opacity: 0;
  transition: opacity 200ms ease;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.8), 0 0 16px rgba(0, 212, 255, 0.4);
}

/* Hover — pill ilumina */
.bottom-nav-btn:hover .nav-pill {
  background: rgba(0, 212, 255, 0.08);
  border-color: rgba(0, 212, 255, 0.15);
  transform: scale(1.06);
}

/* Ativo — pill sólida + indicador visível */
.bottom-nav-btn.active .nav-pill {
  background: rgba(0, 212, 255, 0.12);
  border-color: rgba(0, 212, 255, 0.25);
}

.bottom-nav-btn.active .nav-indicator {
  opacity: 1;
  animation: pulse-glow 2s ease-in-out infinite;
}

/* Ícones */
.bottom-nav-btn svg {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  color: var(--color-text-dim);
  filter: drop-shadow(0 0 3px rgba(0, 212, 255, 0.15));
  transition: filter 200ms ease, color 200ms ease;
}

.bottom-nav-btn:hover svg {
  color: var(--color-text-muted);
  filter: drop-shadow(0 0 6px rgba(0, 212, 255, 0.5));
}

.bottom-nav-btn.active svg {
  color: var(--color-primary);
  filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.8));
}

/* Labels */
.bottom-nav-label {
  font-family: var(--font-data);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  line-height: 1;
  color: var(--color-text-dim);
  transition: color 200ms ease;
}

.bottom-nav-btn:hover .bottom-nav-label {
  color: var(--color-text-muted);
}

.bottom-nav-btn.active .bottom-nav-label {
  color: var(--color-primary);
}
```

**Step 2: Verificar visualmente**

Abrir `localhost:8000` no browser, navegar para qualquer página interna. Verificar:
- Botões têm pill visível ao hover
- Botão ativo tem pill + borda ciano + barra indicadora no topo
- Ícones têm glow sutil

**Step 3: Commit**

```bash
git add frontend/css/app.css
git commit -m "style(frontend): redesign bottom nav com pill, glow e barra indicadora"
```

---

## Task 2: Atualizar estrutura HTML dos botões em `index.html`

**Files:**
- Modify: `frontend/index.html` (linhas 139–163, bloco `<nav class="bottom-nav">`)

**Step 1: Substituir o bloco `<nav class="bottom-nav">` inteiro**

Localizar o bloco atual e substituir por:

```html
    <!-- Bottom Navigation (só fora da home) -->
    <nav class="bottom-nav" x-show="currentPage !== 'home'" x-cloak>
      <button class="bottom-nav-btn" :class="{ active: currentPage === 'abordagem-nova' }" @click="navigate('abordagem-nova')">
        <div class="nav-pill">
          <div class="nav-indicator"></div>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>
          <span class="bottom-nav-label">Abordagem</span>
        </div>
      </button>

      <button class="bottom-nav-btn" :class="{ active: currentPage === 'consulta' }" @click="navigate('consulta')">
        <div class="nav-pill">
          <div class="nav-indicator"></div>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <span class="bottom-nav-label">Consulta IA</span>
        </div>
      </button>

      <button class="bottom-nav-btn" :class="{ active: currentPage === 'home' }" @click="navigate('home')">
        <div class="nav-pill">
          <div class="nav-indicator"></div>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
          <span class="bottom-nav-label">Início</span>
        </div>
      </button>

      <button class="bottom-nav-btn" :class="{ active: currentPage === 'ocorrencia-upload' }" @click="navigate('ocorrencia-upload')">
        <div class="nav-pill">
          <div class="nav-indicator"></div>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M12 12v6"/><path d="m15 15-3-3-3 3"/></svg>
          <span class="bottom-nav-label">Ocorrência</span>
        </div>
      </button>

      <button class="bottom-nav-btn" :class="{ active: currentPage === 'dashboard' }" @click="navigate('dashboard')">
        <div class="nav-pill">
          <div class="nav-indicator"></div>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
          <span class="bottom-nav-label">Analítico</span>
        </div>
      </button>
    </nav>
```

**Step 2: Bumpar versão do CSS no `<link>` do app.css**

Localizar:
```html
<link rel="stylesheet" href="/css/app.css?v=6">
```

Substituir por:
```html
<link rel="stylesheet" href="/css/app.css?v=7">
```

**Step 3: Verificar visualmente (checklist)**

- [ ] Todos os 5 botões têm pill visível no hover
- [ ] Botão ativo tem pill com fundo + borda ciano
- [ ] Barra indicadora aparece no topo da pill do botão ativo
- [ ] Barra pisca suavemente (animação pulse-glow)
- [ ] Ícones têm glow ao hover e no ativo
- [ ] Labels ficam ciano no botão ativo
- [ ] Transição suave ao trocar de página

**Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "style(frontend): adicionar estrutura pill + indicador no bottom nav"
```
