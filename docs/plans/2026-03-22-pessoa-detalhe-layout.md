# Pessoa Detalhe — Layout Visual Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Melhorar legibilidade e consistência visual da página de detalhe de pessoa com sistema de LED animado, padding consistente, thumbnails padronizados e botão de vínculo discreto.

**Architecture:** Duas classes CSS globais (`.card-led-blue`, `.card-led-purple`) adicionadas ao `app.css` para o efeito LED pulsante. Todos os ajustes de padding, gap, thumbnails e botão são feitos inline no `pessoa-detalhe.js`, removendo as `border-left` hardcoded e substituindo pelas classes CSS.

**Tech Stack:** HTML/CSS (keyframes, box-shadow), Alpine.js, Tailwind-like inline styles.

---

### Task 1: Adicionar classes LED ao `app.css`

**Files:**
- Modify: `frontend/css/app.css` (após linha 180, depois de `.glass-card:hover`)

**Step 1: Adicionar as duas classes e keyframes após `.glass-card:hover {}`**

```css
/* LED azul — containers pai (nível 1) */
.card-led-blue {
  border-left: 3px solid #00D4FF;
  animation: led-pulse-blue 2.5s ease-in-out infinite;
}

@keyframes led-pulse-blue {
  0%, 100% { box-shadow: -3px 0 8px rgba(0, 212, 255, 0.4); }
  50%       { box-shadow: -3px 0 14px rgba(0, 212, 255, 0.8), -1px 0 4px rgba(0, 212, 255, 0.3); }
}

/* LED roxo — containers filho (nível 2, cards internos) */
.card-led-purple {
  border-left: 3px solid #A78BFA;
  animation: led-pulse-purple 2.5s ease-in-out infinite;
}

@keyframes led-pulse-purple {
  0%, 100% { box-shadow: -3px 0 8px rgba(167, 139, 250, 0.35); }
  50%       { box-shadow: -3px 0 14px rgba(167, 139, 250, 0.7), -1px 0 4px rgba(167, 139, 250, 0.25); }
}
```

**Step 2: Verificar no browser**

Abrir `http://localhost:8000`, inspecionar qualquer `.glass-card` e adicionar manualmente a classe `card-led-blue` no DevTools para confirmar que o LED azul pulsa corretamente.

**Step 3: Commit**

```bash
git add frontend/css/app.css
git commit -m "feat(frontend): adicionar classes card-led-blue e card-led-purple com animação LED"
```

---

### Task 2: Aplicar `.card-led-blue` nos containers pai e corrigir padding/gap

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Context:** Todos os `glass-card` de nível 1 (containers externos) hoje têm `border-left` hardcoded inline. Vamos substituir pela classe e padronizar o padding.

**Step 1: Localizar todos os `glass-card` de nível 1**

São 7 containers pai na página:
1. **Dados Pessoais** — linha ~43
2. **Fotos** — linha ~70
3. **Endereços** — linha ~313
4. **Veículos Vinculados** — linha ~336
5. **Vínculos** — linha ~365
6. **Histórico de Abordagens** — linha ~470
7. **Mapa de Abordagens** — linha ~551

**Step 2: Para cada `glass-card`, fazer as seguintes substituições**

Padrão atual (varia por container):
```js
class="glass-card" style="border-left: 3px solid var(--color-primary); display: flex; flex-direction: column; gap: 0.5rem;"
```

Padrão novo (unificado):
```js
class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;"
```

Fazer isso para todos os 7 containers, removendo o `border-left` inline e ajustando `gap` para `0.75rem`.

**Step 3: Atualizar os títulos `h3` de seção para ter separador visual**

Padrão atual:
```js
style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;"
```

Padrão novo (adicionar `padding-bottom` e `border-bottom`):
```js
style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);"
```

Aplicar em todos os `h3` de seção dentro dos glass-cards.

**Step 4: Verificar no browser**

Acessar `http://localhost:8000/#pessoa-detalhe` com um abordado cadastrado. Confirmar que os containers pai pulsam em azul e têm padding interno.

**Step 5: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): aplicar card-led-blue nos containers pai com padding e gap consistentes"
```

---

### Task 3: Aplicar `.card-led-purple` nos cards filhos

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Context:** Os cards internos (itens individuais dentro dos glass-cards) hoje usam `border` + `PALETTE[idx % PALETTE.length]` para colorir a borda esquerda. Vamos substituir pela classe `.card-led-purple`.

**Step 1: Cards de endereço (linha ~319)**

Padrão atual:
```js
style="border: 1px solid var(--color-border); border-radius: 4px; padding: 0.75rem;" :style="PALETTE[idx % PALETTE.length]"
```

Padrão novo (classe + remover `:style` do PALETTE):
```js
class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;"
```

**Step 2: Cards de veículos (linha ~342)**

Padrão atual:
```js
style="display: flex; align-items: center; border: 1px solid var(--color-border); border-radius: 4px; padding: 0.75rem;" :style="PALETTE[idx % PALETTE.length]"
```

Padrão novo:
```js
class="card-led-purple" style="display: flex; align-items: center; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;"
```

**Step 3: Cards de vínculos em abordagem (linha ~383)**

Padrão atual:
```js
style="display: flex; align-items: center; justify-content: space-between; border: 1px solid var(--color-border); border-left: 3px solid var(--color-secondary); border-radius: 4px; padding: 0.75rem; cursor: pointer;"
```

Padrão novo:
```js
class="card-led-purple" style="display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; cursor: pointer;"
```

**Step 4: Cards de vínculos manuais (linha ~422)**

Padrão atual:
```js
style="display: flex; align-items: flex-start; justify-content: space-between; border: 1px solid var(--color-border); border-left: 3px solid #A78BFA; border-radius: 4px; padding: 0.75rem; cursor: pointer;"
```

Padrão novo:
```js
class="card-led-purple" style="display: flex; align-items: flex-start; justify-content: space-between; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; cursor: pointer;"
```

**Step 5: Cards de abordagens individuais (linha ~476)**

Padrão atual:
```js
style="border: 1px solid var(--color-border); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;" :style="PALETTE[idx % PALETTE.length]"
```

Padrão novo:
```js
class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;"
```

**Step 6: Verificar e remover a constante `PALETTE` do topo do arquivo se não for mais usada**

Buscar por `PALETTE` no arquivo — se não houver mais usos, remover as linhas 8-17.

**Step 7: Verificar no browser**

Confirmar que cards filhos pulsam em roxo, containers pai em azul, e a hierarquia visual está clara.

**Step 8: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): aplicar card-led-purple nos cards filhos e remover PALETTE"
```

---

### Task 4: Padronizar thumbnails

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Fotos no grid de abordado (linha ~118)**

Atual: `style="width: 100%; height: 7rem; object-fit: cover; border-radius: 4px; cursor: pointer;"`

Novo: `style="width: 100%; height: 5rem; object-fit: cover; border-radius: 4px; cursor: pointer;"`

**Step 2: Thumbnail de veículo (linha ~349)**

Atual: `style="width: 4rem; height: 4rem; object-fit: cover; border-radius: 4px; cursor: pointer; margin-top: 0.25rem;"`

Novo: `style="width: 3.5rem; height: 3.5rem; object-fit: cover; border-radius: 4px; cursor: pointer; margin-top: 0.25rem;"`

**Step 3: Avatar em vínculos de abordagem — img (linha ~388)**

Atual: `style="width: 2rem; height: 2rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border); flex-shrink: 0;"`

Novo: `style="width: 2.5rem; height: 2.5rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border); flex-shrink: 0;"`

Aplicar o mesmo `2.5rem × 2.5rem` para os `div` placeholder sem foto correspondentes.

**Step 4: Avatar em vínculos manuais — img (linha ~426)**

Mesma mudança: `2rem → 2.5rem` para img e div placeholder.

**Step 5: Avatar na busca do modal de vínculo (linha ~220)**

Atual: `style="width: 1.75rem; height: 1.75rem; ..."`

Novo: `style="width: 2rem; height: 2rem; ..."`

**Step 6: Verificar no browser**

Confirmar que todas as thumbnails estão proporcionais e uniformes.

**Step 7: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): padronizar tamanhos de thumbnails na página pessoa-detalhe"
```

---

### Task 5: Substituir botão "Adicionar Vínculo"

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (linha ~368)

**Step 1: Localizar o botão atual**

```js
<button @click="abrirModalVinculo()"
        class="btn btn-primary"
        style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px;">
  + Adicionar
</button>
```

**Step 2: Substituir por link de texto discreto**

```js
<button @click="abrirModalVinculo()"
        style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
        onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
  + Adicionar Vínculo
</button>
```

**Step 3: Verificar no browser**

Confirmar que o botão está discreto no canto superior direito, clicável, e abre o modal normalmente.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): substituir botão Adicionar Vínculo por link de texto discreto"
```

---

### Task 6: Melhorias adicionais — badge "Atual" e placa destacada

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Badge "Atual" no endereço (linha ~328)**

Atual:
```js
<span x-show="idx === 0" style="color: var(--color-primary); font-weight: 500;">Atual</span>
```

Novo:
```js
<span x-show="idx === 0"
      style="font-size: 10px; color: var(--color-primary); font-weight: 600; font-family: var(--font-data); background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); padding: 0 0.375rem; border-radius: 2px; letter-spacing: 0.05em; text-transform: uppercase;">
  Atual
</span>
```

**Step 2: Placa do veículo destacada (linha ~345)**

Atual:
```js
<span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.1em;" x-text="formatPlaca(v.placa)"></span>
```

Novo:
```js
<span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.1em; background: var(--color-surface-hover); padding: 0.125rem 0.375rem; border-radius: 2px; border: 1px solid var(--color-border);" x-text="formatPlaca(v.placa)"></span>
```

Aplicar o mesmo estilo de placa no histórico de abordagens (linha ~503).

**Step 3: Verificar no browser**

Confirmar que "Atual" aparece como badge e as placas têm destaque visual.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): adicionar badge Atual e destaque visual nas placas de veículo"
```

---

### Task 7: Verificação final

**Step 1: Revisão completa no browser**

Acessar `http://localhost:8000/#pessoa-detalhe` com um abordado que tenha: foto, endereço, veículo, vínculos e histórico de abordagens.

Checklist visual:
- [ ] Containers pai pulsam em azul
- [ ] Cards filhos pulsam em roxo
- [ ] Padding interno uniforme (textos não colam nas bordas)
- [ ] Fotos do grid com altura `5rem`
- [ ] Thumbnail de veículo `3.5rem`
- [ ] Avatares de vínculo `2.5rem`
- [ ] Botão "Adicionar Vínculo" discreto, sem fundo
- [ ] Badge "Atual" com borda azul
- [ ] Placas com fundo destacado
- [ ] `PALETTE` removida se não usada

**Step 2: Checar mobile (DevTools > 390px)**

Confirmar que nada quebra em tela pequena.
