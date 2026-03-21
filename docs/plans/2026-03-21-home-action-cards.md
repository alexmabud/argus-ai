# Home Action Cards — Modernização Visual

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir os 4 cards genéricos da home por cards glass + HUD tático com clip-path, scan line, glow e animação de entrada em stagger.

**Architecture:** CSS puro via nova classe `.home-action-card` em `app.css`; `renderHomePage()` em `app.js` refatorado para usar a classe e injetar código tático + dot decorativo por card. Nenhuma dependência nova.

**Tech Stack:** CSS3 (clip-path, backdrop-filter, keyframes, pseudo-elementos), Alpine.js/vanilla JS inline HTML

---

### Task 1: Adicionar keyframes e classe `.home-action-card` no CSS

**Files:**
- Modify: `frontend/css/app.css` (final do arquivo, após a seção `SCROLLBAR CUSTOM`)

**Step 1: Abrir o arquivo e localizar o final**

Arquivo: [frontend/css/app.css](frontend/css/app.css)
Localizar a última linha do arquivo (linha ~922) e adicionar bloco novo após ela.

**Step 2: Adicionar o bloco CSS completo**

```css
/* ========================================
   HOME ACTION CARDS
   ======================================== */
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes card-scan {
  from { top: -40px; opacity: 0.6; }
  to   { top: 100%;  opacity: 0;   }
}

.home-action-card {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 16px;
  background: rgba(13, 21, 32, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 212, 255, 0.15);
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  cursor: pointer;
  transition: border-color 200ms ease, box-shadow 200ms ease, transform 200ms ease;
  animation: card-enter 250ms ease-out both;
}

/* Scan line — pseudo-elemento que desce no hover */
.home-action-card::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(transparent, rgba(0, 212, 255, 0.06), transparent);
  top: -40px;
  pointer-events: none;
}

.home-action-card:hover {
  border-color: rgba(0, 212, 255, 0.5);
  box-shadow:
    0 0 16px rgba(0, 212, 255, 0.12),
    inset 0 0 20px rgba(0, 212, 255, 0.04);
  transform: translateY(-2px);
}

.home-action-card:hover::after {
  animation: card-scan 0.4s ease forwards;
}

.home-action-card:active {
  transform: translateY(0);
}

/* Cabeçalho tático: código + dot */
.home-action-card .card-code {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 14px;
  font-family: var(--font-display);
  font-size: 9px;
  color: var(--color-text-dim);
  letter-spacing: 0.05em;
}

/* Ícone com glow sutil */
.home-action-card .card-icon {
  color: var(--color-primary);
  margin-bottom: 10px;
  filter: drop-shadow(0 0 4px rgba(0, 212, 255, 0.35));
  transition: filter 200ms ease;
}

.home-action-card:hover .card-icon {
  filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.7));
}

/* Label */
.home-action-card .card-label {
  font-family: var(--font-data);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
```

**Step 3: Verificação visual rápida**

Abrir o navegador na home. Os cards ainda terão o visual antigo — o CSS novo só será aplicado após a Task 2.

**Step 4: Commit**

```bash
git add frontend/css/app.css
git commit -m "style(frontend): adicionar classe home-action-card com glass + HUD tático"
```

---

### Task 2: Refatorar `renderHomePage()` em `app.js`

**Files:**
- Modify: `frontend/js/app.js` — função `renderHomePage` (linhas 279–336)

**Step 1: Substituir a função completa**

Localizar a função `renderHomePage` e substituir pelo código abaixo.

Código completo da nova função:

```javascript
/**
 * Renderiza a home page com saudacao e acoes rapidas.
 *
 * Cards no estilo glass + HUD tatico: fundo glassmorphism, clip-path no canto
 * inferior direito, scan line no hover, codigo tatico e glow no icone.
 * Animacao de entrada em stagger (60ms por card).
 */
function renderHomePage(appState) {
  const user = appState.user;
  const abrev = user?.posto_graduacao ? (POSTO_ABREV[user.posto_graduacao] ?? user.posto_graduacao) : null;
  const guerra = user?.nome_guerra || user?.nome || "Agente";
  const saudacao = abrev ? `${abrev} ${guerra}` : guerra;

  const cards = [
    {
      code: '// ABD',
      page: 'abordagem-nova',
      label: 'Nova Abordagem',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>`,
    },
    {
      code: '// IA',
      page: 'consulta',
      label: 'Consulta IA',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
    },
    {
      code: '// OCR',
      page: 'ocorrencia-upload',
      label: 'Ocorr\u00eancia',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M12 12v6"/><path d="m15 15-3-3-3 3"/></svg>`,
    },
    {
      code: '// ANL',
      page: 'dashboard',
      label: 'Anal\u00edtico',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>`,
    },
  ];

  const cardsHtml = cards.map((c, i) => `
    <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('${c.page}')"
            class="home-action-card"
            style="animation-delay: ${i * 60}ms;">
      <div class="card-code">
        <span>${c.code}</span>
        <span>\u25c6</span>
      </div>
      <div class="card-icon">${c.icon}</div>
      <span class="card-label">${c.label}</span>
    </button>
  `).join('');

  return `
    <div class="home-layout">
      <div class="login-scan-line"></div>

      <div style="margin-bottom: 32px;">
        <h2 style="font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--color-text);">
          Ola, <span style="color: var(--color-primary);">${saudacao}</span>
        </h2>
        <p style="font-family: var(--font-data); font-size: 13px; color: var(--color-text-dim); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.08em;">
          Memoria Operacional // Status Ativo
        </p>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
        ${cardsHtml}
      </div>
    </div>
  `;
}
```

**Step 2: Verificação visual no navegador**

Navegar para a home e conferir:
- [ ] 4 cards com fundo glass (translúcido com blur)
- [ ] Canto inferior-direito de cada card cortado em diagonal (~12px)
- [ ] Cabeçalho com código tático (`// ABD`, `// IA`, `// OCR`, `// ANL`) e `◆` à direita
- [ ] Ícone com glow sutil ciano
- [ ] Label em Rajdhani uppercase
- [ ] Ao hover: borda brilha, card sobe levemente, scan line desce, ícone intensifica glow
- [ ] Cards entram em stagger (animação sequencial) ao abrir a home
- [ ] Clicar em cada card navega corretamente

**Step 3: Commit**

```bash
git add frontend/js/app.js
git commit -m "style(frontend): modernizar home action cards com glass + HUD tático e stagger"
```

---

### Task 3: Bump de versão no script src (cache busting)

**Files:**
- Modify: `frontend/index.html` — linha com `app.js` e `app.css`

**Step 1: Incrementar versão**

Localizar no `index.html`:
```html
<link rel="stylesheet" href="/css/app.css?v=8">
```
e
```html
<script src="/js/app.js?v=7"></script>
```

Alterar para:
```html
<link rel="stylesheet" href="/css/app.css?v=9">
```
```html
<script src="/js/app.js?v=8"></script>
```

**Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "chore(frontend): bump versão css e app.js para cache busting"
```

---

## Verificação Final

Após as 3 tasks, conferir na home:
1. Visual dos cards correto (glass, clip-path, código tático, glow)
2. Hover funciona (borda, elevação, scan line, glow do ícone)
3. Animação stagger visível ao navegar para home
4. Navegação de cada card funciona (abordagem-nova, consulta, ocorrencia-upload, dashboard)
5. Sem erros no console do navegador
