# Design System Containers e Legendas de Foto — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Padronizar a página de detalhe de pessoa com design system consistente: containers com borda colorida lateral por tipo de dado, e legenda de data abaixo de cada foto.

**Architecture:** Todas as mudanças são exclusivamente no template HTML dentro de `frontend/js/pages/pessoa-detalhe.js`. Nenhuma alteração de backend, API, schema ou testes necessária. As mudanças são CSS classes Tailwind e pequenos ajustes de markup HTML.

**Tech Stack:** Alpine.js, Tailwind CSS (via CDN), Vanilla JS.

---

### Task 1: Dados Pessoais — adicionar borda colorida no card

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:32`

**Contexto:**
O card de Dados Pessoais usa `class="card space-y-2"`. A classe `card` já é definida no CSS global (provavelmente em `index.html` ou CSS inline). Basta adicionar `border-l-4 border-l-slate-400` às classes existentes.

**Step 1: Localizar a linha**

No arquivo `frontend/js/pages/pessoa-detalhe.js`, linha ~32, encontrar:
```html
<div class="card space-y-2">
  <h3 class="text-sm font-semibold text-slate-300">Dados Pessoais</h3>
```

**Step 2: Aplicar a mudança**

Alterar para:
```html
<div class="card space-y-2 border-l-4 border-l-slate-400">
  <h3 class="text-sm font-semibold text-slate-300">Dados Pessoais</h3>
```

**Step 3: Verificação manual**

Abrir o app, consultar qualquer pessoa, confirmar que o card "Dados Pessoais" tem uma borda vertical cinza à esquerda.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): borda colorida em Dados Pessoais (design system)"
```

---

### Task 2: Fotos do abordado — borda colorida + legenda de data

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:59-73`

**Contexto:**
A seção de fotos tem o card externo com `class="card space-y-2"` e cada foto é um `<div class="relative">` com uma `<img>` e um `<span>` overlay de tipo. O objetivo é:
1. Adicionar `border-l-4 border-l-amber-500` ao card externo
2. Adicionar um `<p>` com a data abaixo de cada `<img>`

**Step 1: Localizar a seção**

Linha ~59-73:
```html
<div x-show="fotos.length > 0" class="card space-y-2">
  <h3 class="text-sm font-semibold text-slate-300">
    Fotos (<span x-text="fotos.length"></span>)
  </h3>
  <div class="grid grid-cols-3 gap-2">
    <template x-for="foto in fotos" :key="foto.id">
      <div class="relative">
        <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
             @click="fotoAmpliada = foto.arquivo_url">
        <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
              x-text="foto.tipo || 'foto'"></span>
      </div>
    </template>
  </div>
</div>
```

**Step 2: Aplicar as mudanças**

```html
<div x-show="fotos.length > 0" class="card space-y-2 border-l-4 border-l-amber-500">
  <h3 class="text-sm font-semibold text-slate-300">
    Fotos (<span x-text="fotos.length"></span>)
  </h3>
  <div class="grid grid-cols-3 gap-2">
    <template x-for="foto in fotos" :key="foto.id">
      <div>
        <div class="relative">
          <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
               @click="fotoAmpliada = foto.arquivo_url">
          <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                x-text="foto.tipo || 'foto'"></span>
        </div>
        <p class="text-xs text-slate-400 text-center mt-1"
           x-text="new Date(foto.criado_em).toLocaleDateString('pt-BR')"></p>
      </div>
    </template>
  </div>
</div>
```

Mudanças:
- Card externo: `border-l-4 border-l-amber-500` adicionado
- Cada foto: `<div class="relative">` envolto em `<div>` pai (sem `relative`)
- Adicionado `<p>` com data abaixo da imagem

**Step 3: Verificação manual**

Consultar pessoa com fotos. Confirmar: borda âmbar no card, data legível abaixo de cada foto, badge de tipo ainda aparece sobreposto.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): borda âmbar e legenda de data em fotos do abordado"
```

---

### Task 3: Endereços — container por item com borda azul

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:82-102`

**Contexto:**
Atualmente cada endereço usa `border-l-2 pl-3 py-1` (só borda vertical simples). Deve ser substituído por container completo com borda ao redor e borda esquerda azul.

**Step 1: Localizar a seção**

Linha ~87-100:
```html
<template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
  <div class="border-l-2 pl-3 py-1"
       :class="idx === 0 ? 'border-blue-500' : 'border-slate-600'">
    <p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
    <div class="flex items-center justify-between text-[10px] mt-0.5">
      <div class="flex gap-3 text-slate-500">
        <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
        <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
        <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
      </div>
      <span x-show="end.criado_em" class="text-xs text-slate-500" x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
    </div>
  </div>
</template>
```

**Step 2: Aplicar a mudança**

Substituir pelo container completo — todos os endereços usam a mesma borda azul; o badge "Atual" já distingue o principal:

```html
<template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
  <div class="border border-slate-700/40 border-l-4 border-l-blue-500 rounded-lg p-3">
    <p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
    <div class="flex items-center justify-between text-[10px] mt-0.5">
      <div class="flex gap-3 text-slate-500">
        <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
        <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
        <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
      </div>
      <span x-show="end.criado_em" class="text-xs text-slate-500" x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
    </div>
  </div>
</template>
```

**Step 3: Verificação manual**

Consultar pessoa com múltiplos endereços. Cada endereço em container próprio com borda azul. Badge "Atual" no primeiro.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): container por endereço com borda azul (design system)"
```

---

### Task 4: Veículos vinculados — container por item com borda verde

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:104-122`

**Contexto:**
Cada veículo usa `flex items-center justify-between bg-slate-800/50 rounded-lg p-2`. Substituir pelo container padronizado com borda verde.

**Step 1: Localizar a seção**

Linha ~110-120:
```html
<template x-for="v in veiculos" :key="v.id">
  <div class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2">
    <div>
      <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
      <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
    </div>
    <span x-show="v.criado_em" class="text-xs text-slate-500"
          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
  </div>
</template>
```

**Step 2: Aplicar a mudança**

```html
<template x-for="v in veiculos" :key="v.id">
  <div class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-green-500 rounded-lg p-3">
    <div>
      <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
      <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
    </div>
    <span x-show="v.criado_em" class="text-xs text-slate-500"
          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
  </div>
</template>
```

**Step 3: Verificação manual**

Consultar pessoa com veículos. Cada veículo em container com borda verde, placa em mono/bold, dados à esquerda, data à direita.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): container por veículo com borda verde (design system)"
```

---

### Task 5: Fotos de Veículos — borda colorida + legenda de data

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:124-139`

**Contexto:**
Mesmo padrão da Task 2, mas para fotos de veículos. O badge de tipo (`veiculo`, `placa`) permanece como overlay.

**Step 1: Localizar a seção**

Linha ~124-139:
```html
<div x-show="fotosVeiculos.length > 0" class="card space-y-2">
  <h3 class="text-sm font-semibold text-slate-300">
    Fotos de Veículos (<span x-text="fotosVeiculos.length"></span>)
  </h3>
  <div class="grid grid-cols-3 gap-2">
    <template x-for="foto in fotosVeiculos" :key="foto.id">
      <div class="relative">
        <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
             @click="fotoAmpliada = foto.arquivo_url">
        <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
              x-text="foto.tipo"></span>
      </div>
    </template>
  </div>
</div>
```

**Step 2: Aplicar as mudanças**

```html
<div x-show="fotosVeiculos.length > 0" class="card space-y-2 border-l-4 border-l-teal-500">
  <h3 class="text-sm font-semibold text-slate-300">
    Fotos de Veículos (<span x-text="fotosVeiculos.length"></span>)
  </h3>
  <div class="grid grid-cols-3 gap-2">
    <template x-for="foto in fotosVeiculos" :key="foto.id">
      <div>
        <div class="relative">
          <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
               @click="fotoAmpliada = foto.arquivo_url">
          <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                x-text="foto.tipo"></span>
        </div>
        <p class="text-xs text-slate-400 text-center mt-1"
           x-text="new Date(foto.criado_em).toLocaleDateString('pt-BR')"></p>
      </div>
    </template>
  </div>
</div>
```

**Step 3: Verificação manual**

Consultar pessoa com veículo com fotos. Confirmar: borda teal no card, data abaixo de cada foto, badge de tipo sobreposto.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): borda teal e legenda de data em fotos de veículos"
```

---

### Task 6: Vínculos (relacionamentos) — container por item com borda laranja

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:141-158`

**Contexto:**
Cada vínculo usa `flex items-center justify-between bg-slate-800/50 rounded-lg p-2 cursor-pointer hover:bg-slate-700/50`. Substituir pelo container padronizado com borda laranja, mantendo cursor pointer e hover.

**Step 1: Localizar a seção**

Linha ~147-157:
```html
<template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
  <div @click="viewPessoa(rel.pessoa_id)" class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2 cursor-pointer hover:bg-slate-700/50">
    <span class="text-sm text-slate-300" x-text="rel.nome"></span>
    <div class="text-right">
      <span class="text-xs text-blue-400 font-medium" x-text="rel.frequencia + 'x juntos'"></span>
      <p x-show="rel.ultima_vez" class="text-[10px] text-slate-500"
         x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
    </div>
  </div>
</template>
```

**Step 2: Aplicar a mudança**

```html
<template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
  <div @click="viewPessoa(rel.pessoa_id)" class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-orange-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
    <span class="text-sm text-slate-300" x-text="rel.nome"></span>
    <div class="text-right">
      <span class="text-xs text-blue-400 font-medium" x-text="rel.frequencia + 'x juntos'"></span>
      <p x-show="rel.ultima_vez" class="text-[10px] text-slate-500"
         x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
    </div>
  </div>
</template>
```

**Step 3: Verificação manual**

Consultar pessoa com vínculos. Cada vínculo com borda laranja, clicável, hover funciona.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): container por vínculo com borda laranja (design system)"
```

---

### Task 7: Histórico de Abordagens — container por item com borda roxa

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:160-194`

**Contexto:**
Cada abordagem já usa `border border-slate-700 rounded-lg p-3 space-y-2`. Apenas ajustar a borda para incluir `border-l-4 border-l-purple-500` e suavizar a borda geral para `border-slate-700/40`.

**Step 1: Localizar a seção**

Linha ~166-193:
```html
<template x-for="ab in abordagens" :key="ab.id">
  <div class="border border-slate-700 rounded-lg p-3 space-y-2">
    ...
  </div>
</template>
```

**Step 2: Aplicar a mudança**

Alterar apenas a classe do container de cada abordagem:

```html
<template x-for="ab in abordagens" :key="ab.id">
  <div class="border border-slate-700/40 border-l-4 border-l-purple-500 rounded-lg p-3 space-y-2">
    ...
  </div>
</template>
```

O conteúdo interno (endereço, observação, veículos) permanece idêntico.

**Step 3: Verificação manual**

Consultar pessoa com abordagens. Cada abordagem em container com borda roxa à esquerda.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): borda roxa por abordagem no histórico (design system)"
```

---

## Resumo de arquivos modificados

| Arquivo | Mudanças |
|---|---|
| `frontend/js/pages/pessoa-detalhe.js` | Classes CSS em todos os cards/containers + legenda de data nas fotos |

## Verificação final completa

Após todas as tasks, abrir o app e verificar:

1. **Dados Pessoais** — borda esquerda cinza (`slate-400`)
2. **Fotos do abordado** — borda âmbar, data legível abaixo de cada foto, badge de tipo sobreposto
3. **Endereços** — cada endereço em container próprio, borda azul, badge "Atual" no primeiro
4. **Veículos vinculados** — cada veículo em container, borda verde, placa formatada
5. **Fotos de Veículos** — borda teal, data abaixo de cada foto, badge de tipo sobreposto
6. **Vínculos** — cada vínculo com borda laranja, clicável
7. **Histórico de Abordagens** — cada abordagem com borda roxa
