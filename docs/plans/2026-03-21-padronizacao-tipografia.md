# Padronização Tipográfica e Espaçamentos — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Padronizar font-sizes, unidades e padding de inputs em todo o frontend, usando consulta.js como referência.

**Architecture:** Mudança no CSS global propaga o padding correto para todos os inputs. Correções nos JS files convertem unidades `rem` para `px` equivalentes nos estilos inline. Sem novas dependências.

**Tech Stack:** CSS custom properties, estilos inline em template strings JS (Alpine.js SPA).

---

### Task 1: CSS global — ajustar padding dos inputs

**Files:**
- Modify: `frontend/css/app.css`

**Contexto:** O seletor global `input, textarea, select` usa `padding: 10px 14px`. A consulta (referência) usa `12px` vertical via override inline. Após esta task, todos os campos do sistema terão `12px 14px` automaticamente — sem precisar de overrides inline.

**Step 1: Localizar o bloco no arquivo**

Leia `frontend/css/app.css` e encontre o bloco de inputs (por volta da linha 63):
```css
input, textarea, select {
  background-color: var(--color-bg);
  ...
  padding: 10px 14px;
  ...
}
```

**Step 2: Alterar o padding**

Mudar apenas esta linha:
```css
/* De: */
  padding: 10px 14px;

/* Para: */
  padding: 12px 14px;
```

**Step 3: Commit**
```bash
git add frontend/css/app.css
git commit -m "style(frontend): aumentar padding global de inputs para 12px 14px"
```

---

### Task 2: perfil.js — converter rem para px

**Files:**
- Modify: `frontend/js/pages/perfil.js`

**Contexto:** Toda a função `renderPerfil()` e o modal inline em `mostrarModalSaida()` usam unidades `rem`. Conversão: 1rem = 16px.

**Step 1: Leia o arquivo inteiro para ter o contexto atual**

**Step 2: Substituir todos os valores rem na função `renderPerfil()` (template HTML)**

Linha 28 — container principal:
```js
// De:
<div style="padding: 1rem; max-width: 28rem; margin: 0 auto;" x-data="perfilPage()">
// Para:
<div style="padding: 16px; max-width: 448px; margin: 0 auto;" x-data="perfilPage()">
```

Linha 30 — wrapper da foto:
```js
// De:
<div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 1.5rem;">
// Para:
<div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 24px;">
```

Linha 32 — div do avatar (font-size das iniciais):
```js
// De:
font-size: 1.875rem;
// Para:
font-size: 28px;
```

Linha 52 — texto "Enviando foto...":
```js
// De:
style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: 0.5rem; font-family: var(--font-data);"
// Para:
style="font-size: 12px; color: var(--color-text-muted); margin-top: 8px; font-family: var(--font-data);"
```

Linha 56 — wrapper dos campos de perfil:
```js
// De:
<div style="display: flex; flex-direction: column; gap: 1rem;">
// Para:
<div style="display: flex; flex-direction: column; gap: 16px;">
```

Linha 88 — botão "Gerenciar usuários":
```js
// De:
style="width: 100%; margin-top: 0.25rem;"
// Para:
style="width: 100%; margin-top: 4px;"
```

Linha 95 — seção botão sair:
```js
// De:
<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--color-border);">
// Para:
<div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--color-border);">
```

Linha 97 — botão "Sair do aplicativo":
```js
// De:
style="width: 100%; padding: 0.5rem 1rem; font-family: var(--font-data); font-size: 0.875rem; font-weight: 500; color: var(--color-danger); background: transparent; border: 1px solid var(--color-danger); border-radius: 4px; cursor: pointer; transition: opacity 0.2s;"
// Para:
style="width: 100%; padding: 8px 16px; font-family: var(--font-data); font-size: 14px; font-weight: 500; color: var(--color-danger); background: transparent; border: 1px solid var(--color-danger); border-radius: 4px; cursor: pointer; transition: opacity 0.2s;"
```

**Step 3: Substituir valores rem dentro de `mostrarModalSaida()` (overlay inline)**

Linha 169 — overlay:
```js
// De:
overlay.style.cssText = '...padding:1rem;';
// Para:
overlay.style.cssText = '...padding:16px;';
```

Linha 173 — card do modal:
```js
// De:
style="padding:1.5rem;max-width:24rem;width:100%;border:1px solid var(--color-border);"
// Para:
style="padding:24px;max-width:384px;width:100%;border:1px solid var(--color-border);"
```

Linha 174 — título do modal:
```js
// De:
style="color:var(--color-text);font-family:var(--font-display);font-weight:600;margin-bottom:0.5rem;"
// Para:
style="color:var(--color-text);font-family:var(--font-display);font-weight:600;margin-bottom:8px;"
```

Linha 175 — parágrafo do modal:
```js
// De:
style="color:var(--color-text-muted);font-size:0.875rem;margin-bottom:1.5rem;font-family:var(--font-body);"
// Para:
style="color:var(--color-text-muted);font-size:14px;margin-bottom:24px;font-family:var(--font-body);"
```

Linha 176 — div dos botões do modal:
```js
// De:
<div style="display:flex;gap:0.75rem;">
// Para:
<div style="display:flex;gap:12px;">
```

Linha 178 — botão "Confirmar saída":
```js
// De:
style="flex:1;padding:0.5rem 1rem;border-radius:4px;...
// Para:
style="flex:1;padding:8px 16px;border-radius:4px;...
```

**Step 4: Verificar que não restaram unidades rem**

```bash
grep -n "rem" frontend/js/pages/perfil.js
```
Esperado: nenhuma ocorrência (ou apenas dentro de comentários/strings de texto).

**Step 5: Commit**
```bash
git add frontend/js/pages/perfil.js
git commit -m "style(frontend): converter rem para px em perfil.js"
```

---

### Task 3: ocorrencia-upload.js — converter rem para px

**Files:**
- Modify: `frontend/js/pages/ocorrencia-upload.js`

**Step 1: Leia o arquivo para ter contexto atual**

**Step 2: Substituir os valores rem**

Linha 13 — título h2:
```js
// De:
font-size:1.25rem;
// Para:
font-size:18px;
```

Linha 16 — subtítulo:
```js
// De:
font-size:0.7rem;
// Para:
font-size:12px;
```

Linha 65 — tag de envolvido (`font-size:0.75rem`):
```js
// De:
font-size:0.75rem;
// Para:
font-size:12px;
```

Linha 68 — botão × dentro da tag (`font-size:0.875rem`):
```js
// De:
font-size:0.875rem;
// Para:
font-size:14px;
```

Linha 85 — mensagem de sucesso (`font-size:0.875rem`):
```js
// De:
style="font-size:0.875rem;color:var(--color-success);"
// Para:
style="font-size:14px;color:var(--color-success);"
```

Linha 86 — mensagem de erro (`font-size:0.875rem`):
```js
// De:
style="font-size:0.875rem;color:var(--color-danger);"
// Para:
style="font-size:14px;color:var(--color-danger);"
```

Linha 90 — section header "Buscar Ocorrência" (`font-size:0.85rem`):
```js
// De:
font-size:0.85rem;
// Para:
font-size:12px;
```

**Step 3: Verificar que não restaram unidades rem**

```bash
grep -n "rem" frontend/js/pages/ocorrencia-upload.js
```
Esperado: nenhuma ocorrência.

**Step 4: Commit**
```bash
git add frontend/js/pages/ocorrencia-upload.js
git commit -m "style(frontend): converter rem para px em ocorrencia-upload.js"
```

---

### Task 4: consulta.js — remover overrides de padding/font-size redundantes

**Files:**
- Modify: `frontend/js/pages/consulta.js`

**Contexto:** Após a Task 1, o CSS global já define `padding: 12px 14px` e `font-size: 14px` para todos os inputs. O input principal de busca na consulta tem um override inline `padding-top:12px;padding-bottom:12px;font-size:14px;` que agora é redundante. O `padding-left:40px` deve ser **mantido** (é para o ícone de busca).

**Step 1: Localizar o input de busca em consulta.js (~linha 38)**

```js
style="padding-left:40px;padding-top:12px;padding-bottom:12px;font-size:14px;"
```

**Step 2: Remover os overrides redundantes, manter só o padding-left**

```js
// De:
style="padding-left:40px;padding-top:12px;padding-bottom:12px;font-size:14px;"
// Para:
style="padding-left:40px;"
```

**Step 3: Verificar que o input ainda funciona visualmente** — o padding e font-size vêm agora do CSS global.

**Step 4: Commit**
```bash
git add frontend/js/pages/consulta.js
git commit -m "style(frontend): remover overrides redundantes de padding/font-size em consulta.js"
```

---

## Verificação Final

Após todas as tasks, conferir visualmente nas páginas (com docker compose up ou make dev):

1. **Login**: inputs com altura maior (12px vs 10px anterior) — sutil mas consistente
2. **Perfil**: layout em px sem diferença visual, modal de saída proporcional
3. **Ocorrência**: título `18px` alinhado com outras páginas, textos helper em `12px`/`14px`
4. **Consulta**: input de busca com mesmo padding do restante, ícone continua posicionado

```bash
# Verificação final: não deve restar nenhum rem em páginas JS
grep -rn "rem" frontend/js/pages/
```
Esperado: nenhuma ocorrência.
