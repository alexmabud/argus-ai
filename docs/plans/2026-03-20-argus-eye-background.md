# Argus Eye Background Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Usar a imagem do olho cibernético como fundo do sistema — visível no login (opacity 0.45) e sutil no restante (opacity 0.18), com fade suave entre páginas.

**Architecture:** Um `<img id="argus-eye-bg">` fixo no DOM, com opacidade controlada via Alpine.js lendo `authenticated` (já existente em `app()`). CSS trata posicionamento, blend-mode e vinheta no login. Nenhum componente de página precisa ser alterado.

**Tech Stack:** HTML, CSS (mix-blend-mode, radial-gradient), Alpine.js `:style` + `:class`

---

### Task 1: Adicionar a imagem ao projeto

**Files:**
- Create: `frontend/images/argus-eye.jpg` (o usuário precisa copiar o arquivo)

**Step 1: Criar o diretório de imagens**

```bash
mkdir -p frontend/images
```

**Step 2: Copiar a imagem para o diretório**

O usuário deve copiar o arquivo da imagem do olho para `frontend/images/argus-eye.jpg`.

> Se a imagem for `.webp` ou `.png`, ajuste a extensão nos passos seguintes.

**Step 3: Verificar que o arquivo está acessível**

Com o servidor rodando (`make dev`), acesse `http://localhost:8000/images/argus-eye.jpg` no browser.
Esperado: imagem carrega corretamente.

**Step 4: Commit**

```bash
git add frontend/images/argus-eye.jpg
git commit -m "assets(frontend): adicionar imagem argus-eye para background"
```

---

### Task 2: Adicionar estilos CSS do background

**Files:**
- Modify: `frontend/css/app.css` — após o bloco `/* BACKGROUND EFFECTS */` (linha ~76)

**Step 1: Localizar o bloco de background no CSS**

Abra `frontend/css/app.css` e encontre o comentário:
```css
/* ========================================
   BACKGROUND EFFECTS — Grid + Scan Lines
   ======================================== */
```

**Step 2: Adicionar os estilos do `#argus-eye-bg` antes do `body::before`**

Insira logo após o comentário de BACKGROUND EFFECTS e antes do `body::before`:

```css
/* ========================================
   ARGUS EYE — Background Image
   ======================================== */
#argus-eye-bg {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  z-index: -1;
  pointer-events: none;
  mix-blend-mode: luminosity;
  transition: opacity 0.6s ease;
}
```

**Step 3: Adicionar vinheta para o modo login**

Localize o `body::before` existente:
```css
body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}
```

Substitua por:
```css
body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

body.login-active::before {
  background-image:
    radial-gradient(ellipse at center, transparent 25%, rgba(5, 10, 15, 0.88) 75%),
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
}
```

**Step 4: Verificar que o CSS não quebrou nada**

```bash
make lint
```

Esperado: sem erros de CSS (ruff não valida CSS, verificação é visual).

**Step 5: Commit**

```bash
git add frontend/css/app.css
git commit -m "style(frontend): adicionar estilos do argus-eye background e vinheta login"
```

---

### Task 3: Inserir o elemento `<img>` no HTML e controlar via Alpine.js

**Files:**
- Modify: `frontend/index.html` — logo após `<body ...>` (linha 56) e no `<body>` tag

**Step 1: Adicionar `:class` ao `<body>` para ativar a vinheta no login**

Localize a linha:
```html
<body class="dark" x-data="app()" x-init="init()">
```

Substitua por:
```html
<body class="dark" x-data="app()" x-init="init()" :class="{ 'login-active': !authenticated }">
```

**Step 2: Inserir o `<img>` do olho logo após a abertura do `<body>`**

Logo após a linha do `<body>`, antes do `<!-- Offline indicator -->`, insira:

```html
  <!-- Argus Eye — Background -->
  <img id="argus-eye-bg"
       src="/images/argus-eye.jpg"
       :style="{ opacity: !authenticated ? '0.45' : '0.18' }"
       alt=""
       aria-hidden="true">
```

**Step 3: Bump de versão do CSS para invalidar cache**

Localize:
```html
  <link rel="stylesheet" href="/css/app.css">
```

Substitua por (adicione query string de versão):
```html
  <link rel="stylesheet" href="/css/app.css?v=5">
```

**Step 4: Verificar visualmente**

Com `make dev` rodando:
1. Acesse `http://localhost:8000` — tela de login deve mostrar o olho com opacidade visível e vinheta nas bordas
2. Faça login com `admin001` / `admin123` — o olho deve fazer fade para mais sutil
3. Faça logout — o olho deve voltar a ficar mais visível com vinheta

**Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): adicionar argus-eye como background global com fade por rota"
```

---

### Task 4: Push e deploy

**Step 1: Push para o repositório**

```bash
git push origin main
```

**Step 2: Deploy na VM**

```bash
# 1. Liberar espaço
docker system prune -f

# 2. Puxar mudanças
cd ~/argus_ai && git pull

# 3. Rebuild
docker compose up -d --build
```

**Step 3: Verificar em produção**

Acesse a URL de produção e confirme o mesmo comportamento visual observado localmente.
