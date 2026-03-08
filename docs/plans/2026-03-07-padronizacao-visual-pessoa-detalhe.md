# Padronização Visual — Pessoa Detalhe

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Padronizar posição da data de cadastro, exibir `criado_em` no histórico de abordagens e aplicar sistema de cores cíclicas por item em endereços, veículos e abordagens.

**Architecture:** Todas as mudanças ficam em `frontend/js/pages/pessoa-detalhe.js`. Uma constante `PALETTE` de 8 cores Tailwind é definida no topo do arquivo. O Alpine.js `x-for` usa a sintaxe `(item, idx)` para acessar o índice e aplicar `:class="PALETTE[idx % PALETTE.length]"` em cada item. Nenhuma mudança de backend.

**Tech Stack:** Alpine.js, Tailwind CSS (classes inline — sem interpolação para não quebrar purge), HTML template strings em JS.

---

### Task 1: Definir paleta de cores e aplicar nos cards de seção

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

Adicionar a constante `PALETTE` antes da função `renderPessoaDetalhe` e aplicar borda colorida nos cards de seção (Endereços, Veículos, Abordagens).

**Step 1: Adicionar constante PALETTE no topo do arquivo**

Abrir `frontend/js/pages/pessoa-detalhe.js` e inserir antes de `function renderPessoaDetalhe`:

```js
const PALETTE = [
  'border-l-blue-500',
  'border-l-green-500',
  'border-l-orange-500',
  'border-l-purple-500',
  'border-l-teal-500',
  'border-l-yellow-500',
  'border-l-red-400',
  'border-l-pink-500',
];
```

**Step 2: Aplicar borda colorida nos cards de seção**

Localizar os três `<div class="card space-y-2">` das seções e adicionar a borda esquerda fixa:

- Seção **Endereços** (linha ~87): trocar `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-blue-600"`
- Seção **Veículos** (linha ~109): trocar `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-green-600"`
- Seção **Abordagens** (linha ~170): trocar `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-purple-600"`

**Step 3: Verificar visualmente no browser**

Abrir `http://localhost:8000`, navegar até o detalhe de uma pessoa, confirmar que as 3 seções têm borda colorida no card.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): adicionar borda colorida nos cards de seção (endereços, veículos, abordagens)"
```

---

### Task 2: Cores cíclicas nos itens de Endereços

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:92-105`

**Step 1: Trocar x-for para incluir índice**

Localizar (linha ~92):
```html
<template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
```

Se ainda estiver `x-for="end in pessoa.enderecos"`, trocar para:
```html
<template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
```

**Step 2: Aplicar cor cíclica no container do item**

O `<div>` do item (linha ~93) atualmente é:
```html
<div class="border border-slate-700/40 border-l-4 border-l-blue-500 rounded-lg p-3">
```

Trocar por (remover `border-l-blue-500` do class estático e usar binding dinâmico):
```html
<div class="border border-slate-700/40 border-l-4 rounded-lg p-3" :class="PALETTE[idx % PALETTE.length]">
```

**Step 3: Verificar no browser**

Pessoa com 2+ endereços deve mostrar cores diferentes em cada item.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): cores cíclicas nos itens de endereço"
```

---

### Task 3: Cores cíclicas nos itens de Veículos

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:113-126`

**Step 1: Trocar x-for para incluir índice**

Localizar (linha ~114):
```html
<template x-for="v in veiculos" :key="v.id">
```

Trocar para:
```html
<template x-for="(v, idx) in veiculos" :key="v.id">
```

**Step 2: Aplicar cor cíclica no container do item**

O `<div>` do item (linha ~115) atualmente é:
```html
<div class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-green-500 rounded-lg p-3">
```

Trocar por:
```html
<div class="flex items-center justify-between border border-slate-700/40 border-l-4 rounded-lg p-3" :class="PALETTE[idx % PALETTE.length]">
```

**Step 3: Verificar no browser**

Pessoa com 2+ veículos deve mostrar cores diferentes.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): cores cíclicas nos itens de veículo"
```

---

### Task 4: Cores cíclicas nos itens de Abordagens

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:175-202`

**Step 1: Trocar x-for para incluir índice**

Localizar (linha ~175):
```html
<template x-for="ab in abordagens" :key="ab.id">
```

Trocar para:
```html
<template x-for="(ab, idx) in abordagens" :key="ab.id">
```

**Step 2: Aplicar cor cíclica no container do item**

O `<div>` do item (linha ~176) atualmente é:
```html
<div class="border border-slate-700/40 border-l-4 border-l-purple-500 rounded-lg p-3 space-y-2">
```

Trocar por:
```html
<div class="border border-slate-700/40 border-l-4 rounded-lg p-3 space-y-2" :class="PALETTE[idx % PALETTE.length]">
```

**Step 3: Verificar no browser**

Pessoa com 2+ abordagens deve mostrar cores diferentes.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): cores cíclicas nos itens de abordagem"
```

---

### Task 5: Data de cadastro padronizada — canto superior direito

**Contexto:** Atualmente a data "Cadastrado em" está em posições inconsistentes entre os containers. A regra nova é: **toda linha de topo** do container usa `flex items-center justify-between`, com a info principal à esquerda e a data de cadastro à direita em `text-xs text-slate-500`.

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:92-126`

**Step 1: Padronizar linha de topo nos Endereços**

O item de endereço atual tem:
```html
<p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
<div class="flex items-center justify-between text-[10px] mt-0.5">
  <div class="flex gap-3 text-slate-500">
    <span x-show="end.data_inicio" ...></span>
    <span x-show="end.data_fim" ...></span>
    <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
  </div>
  <span x-show="end.criado_em" class="text-xs text-slate-500" x-text="'Cadastrado em ' + ..."></span>
</div>
```

Reorganizar para colocar a data de cadastro no topo direito:
```html
<div class="flex items-start justify-between gap-2">
  <p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
  <span x-show="end.criado_em" class="text-xs text-slate-500 shrink-0"
        x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
</div>
<div class="flex gap-3 text-[10px] text-slate-500 mt-0.5">
  <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
  <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
  <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
</div>
```

**Step 2: Padronizar linha de topo nos Veículos**

O item de veículo atual tem a data no meio do conteúdo. Reorganizar para:
```html
<div class="flex items-start justify-between gap-2 w-full">
  <div>
    <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
    <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
       x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
  </div>
  <span x-show="v.criado_em" class="text-xs text-slate-500 shrink-0"
        x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
</div>
```

**Step 3: Verificar no browser**

Confirmar que a data aparece no canto superior direito em endereços e veículos.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): padronizar data de cadastro no canto superior direito dos containers"
```

---

### Task 6: Exibir criado_em no histórico de abordagens

**Contexto:** Atualmente o card de abordagem exibe `ab.data_hora` (quando a abordagem ocorreu) sem label, e `ab.criado_em` (quando foi registrada no sistema) não é exibido. O design pede exibir ambos: `data_hora` com label à esquerda, `criado_em` com label "Cadastrada em" no canto superior direito.

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:176-200`

**Step 1: Substituir linha de topo do card de abordagem**

Linha de topo atual (linhas ~177-180):
```html
<div class="flex items-center justify-between">
  <span class="text-xs font-medium text-blue-400" x-text="'#' + ab.id"></span>
  <span class="text-xs text-slate-400" x-text="new Date(ab.data_hora).toLocaleString('pt-BR')"></span>
</div>
```

Trocar por:
```html
<div class="flex items-start justify-between gap-2">
  <div>
    <span class="text-xs font-medium text-blue-400" x-text="'#' + ab.id"></span>
    <span x-show="ab.data_hora" class="text-xs text-slate-400 ml-2"
          x-text="'Data da Abordagem: ' + new Date(ab.data_hora).toLocaleString('pt-BR')"></span>
  </div>
  <span x-show="ab.criado_em" class="text-xs text-slate-500 shrink-0"
        x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
</div>
```

**Step 2: Verificar no browser**

No histórico de abordagens:
- Linha de topo mostra `#id` + "Data da Abordagem: dd/mm/aaaa HH:MM" à esquerda
- Canto superior direito mostra "Cadastrada em dd/mm/aaaa às HH:MM"
- Se `criado_em` não vier da API, o campo fica oculto (x-show)

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): exibir criado_em com label 'Cadastrada em' no histórico de abordagens"
```

---

### Task 7: Revisão visual final

**Step 1: Testar cenário completo**

Com um usuário que tenha:
- 3+ endereços → verificar cores cíclicas diferentes + data no canto superior direito
- 3+ veículos → verificar cores cíclicas diferentes + data no canto superior direito
- 3+ abordagens → verificar cores cíclicas diferentes + "Data da Abordagem" + "Cadastrada em"
- Seções com borda colorida no card (azul, verde, roxo)

**Step 2: Verificar comportamento com dados ausentes**

- Endereço sem `criado_em` → data não aparece (x-show)
- Abordagem sem `criado_em` → "Cadastrada em" não aparece (x-show)
- Veículo sem `criado_em` → data não aparece (x-show)

**Step 3: Commit final se houver ajustes**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): ajustes visuais pós-revisão padronização containers"
```
