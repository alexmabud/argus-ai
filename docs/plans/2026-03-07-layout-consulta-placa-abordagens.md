# Layout Consulta — Placa, Histórico de Abordagens, Datas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ajustar layout da página de detalhe de pessoa: formatar placa no padrão XXX-0000, melhorar exibição do histórico de abordagens com rótulos e layout por linha, e garantir consistência visual nas datas de cadastro.

**Architecture:** Todas as mudanças são exclusivamente no template HTML e lógica JS de `frontend/js/pages/pessoa-detalhe.js`. Nenhuma alteração de backend ou API necessária.

**Tech Stack:** Alpine.js, Tailwind CSS, Vanilla JS.

---

### Task 1: Adicionar função `formatPlaca` e aplicar na seção Veículos Vinculados

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:186-252` (função `pessoaDetalhePage`)

**Contexto:**
A placa vem da API como string sem hífen (ex: `"ABC1234"` ou `"ABC1E23"`). O padrão brasileiro é `XXX-0000` (3 letras + hífen + 4 caracteres). A função deve inserir o hífen na posição 3 se ele ainda não existir.

**Step 1: Adicionar `formatPlaca` no objeto retornado por `pessoaDetalhePage`**

Localizar o método `formatEndereco` (linha ~233) e adicionar logo abaixo:

```js
formatPlaca(placa) {
  if (!placa) return '—';
  const p = placa.toUpperCase().replace('-', '');
  if (p.length >= 4) return p.slice(0, 3) + '-' + p.slice(3);
  return p;
},
```

**Step 2: Aplicar na seção Veículos Vinculados (linha ~113)**

Alterar:
```html
<span class="font-mono font-bold text-slate-100 tracking-wider" x-text="v.placa"></span>
```
Para:
```html
<span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
```

**Step 3: Verificação manual**

Abrir o app, consultar uma pessoa com veículo vinculado e confirmar que a placa aparece como `ABC-1234`.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): formatar placa no padrão XXX-0000 em veículos vinculados"
```

---

### Task 2: Refatorar exibição do Histórico de Abordagens

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:149-175` (template do histórico)

**Contexto:**
Atualmente o histórico de abordagens:
- Mostra `ab.endereco_texto` sem rótulo
- Mostra `ab.observacao` sem rótulo
- Exibe chips de **pessoas** — redundante (prontuário já é da pessoa)
- Exibe chips de **veículos** — sem rótulo, sem hífen na placa

As mudanças:
1. Adicionar rótulo `Endereço da Abordagem:` antes do texto de endereço
2. Adicionar rótulo `Observação:` antes do texto de observação
3. **Remover** o bloco de chips de pessoas (`ab.pessoas`)
4. **Substituir** chips de veículos por lista de linhas (uma por veículo), placa formatada, sem referenciar dono

**Step 1: Substituir o bloco interno de cada abordagem (linhas 154–173)**

Localizar o trecho dentro do `<template x-for="ab in abordagens"` e substituir:

```html
<!-- ANTES -->
<p x-show="ab.endereco_texto" class="text-xs text-slate-400" x-text="ab.endereco_texto"></p>
<p x-show="ab.observacao" class="text-xs text-slate-300" x-text="ab.observacao"></p>

<!-- Pessoas nesta abordagem -->
<div x-show="ab.pessoas?.length > 0" class="flex flex-wrap gap-1">
  <template x-for="ap in ab.pessoas" :key="ap.id">
    <span class="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
          x-text="ap.nome"></span>
  </template>
</div>

<!-- Veículos nesta abordagem -->
<div x-show="ab.veiculos?.length > 0" class="flex flex-wrap gap-1">
  <template x-for="av in ab.veiculos" :key="av.id">
    <span class="text-[10px] bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded font-mono"
          x-text="av.placa"></span>
  </template>
</div>
```

Por:

```html
<!-- Endereço da Abordagem -->
<div x-show="ab.endereco_texto" class="text-xs">
  <span class="text-slate-500 font-medium">Endereço da Abordagem:</span>
  <span class="text-slate-400 ml-1" x-text="ab.endereco_texto"></span>
</div>

<!-- Observação -->
<div x-show="ab.observacao" class="text-xs">
  <span class="text-slate-500 font-medium">Observação:</span>
  <span class="text-slate-300 ml-1" x-text="ab.observacao"></span>
</div>

<!-- Veículos nesta abordagem (um por linha, sem dono) -->
<div x-show="ab.veiculos?.length > 0" class="space-y-0.5">
  <template x-for="av in ab.veiculos" :key="av.id">
    <div class="text-xs text-slate-400"
         x-text="[formatPlaca(av.placa), av.modelo, av.cor, av.ano].filter(Boolean).join(' · ')"></div>
  </template>
</div>
```

**Step 2: Verificação manual**

Consultar uma pessoa com abordagens que tenham endereço, observação e veículo. Confirmar:
- Rótulos aparecem
- Chips de pessoas sumiram
- Veículos aparecem uma linha por vez, placa com hífen

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): refatorar histórico de abordagens — rótulos, remover chips redundantes, veículo por linha"
```

---

### Task 3: Verificar consistência das datas "Cadastrado em"

**Files:**
- Review: `frontend/js/pages/pessoa-detalhe.js:91-99` (endereços) e `117-119` (veículos)

**Contexto:**
O usuário pediu para manter o mesmo padrão de letra, tamanho e alinhamento nas datas "Cadastrado em" dos cards de Endereços e Veículos.

**Step 1: Verificar e alinhar estilos**

Confirmar que ambos usam exatamente:
- Classe: `text-xs text-slate-500`
- Alinhamento: `text-right` implícito pelo `flex justify-between` do container pai

Endereços (linha ~97):
```html
<span x-show="end.criado_em" class="text-slate-500 text-xs"
      x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
```

Veículos (linha ~117):
```html
<span x-show="v.criado_em" class="text-xs text-slate-500"
      x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
```

Se as classes estiverem em ordem diferente, uniformizar para `class="text-xs text-slate-500"` em ambos. O alinhamento à direita já é garantido pelo container `flex items-center justify-between`.

**Step 2: Commit (só se houver mudança)**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): uniformizar estilo das datas Cadastrado em (endereço e veículo)"
```

---

## Resumo de arquivos modificados

| Arquivo | Mudanças |
|---|---|
| `frontend/js/pages/pessoa-detalhe.js` | Função `formatPlaca`, placa formatada em veículos, rótulos no histórico, remoção de chips de pessoas, veículos por linha |

## Verificação final

Após as 3 tasks, abrir o app e testar:
1. Pessoa com veículo → placa aparece `XXX-0000` no card de veículos
2. Pessoa com abordagem com endereço/observação/veículo → rótulos presentes, chips de pessoas ausentes, veículo em linha com placa formatada
3. Cards de endereço e veículo → datas "Cadastrado em" com mesmo tamanho e alinhamento
