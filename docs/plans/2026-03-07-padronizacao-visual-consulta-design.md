# Design: Padronização Visual — Página de Consulta / Detalhe de Pessoa

**Data:** 2026-03-07
**Arquivo principal:** `frontend/js/pages/pessoa-detalhe.js`

## Escopo

Três melhorias visuais na página de detalhe de pessoa e na página de consulta:

1. Data de cadastro padronizada no canto superior direito de cada container
2. Campo "Cadastrada em" no histórico de abordagens (separado da data_hora)
3. Sistema de cores cíclicas por item (endereços, veículos, abordagens)

---

## 1. Data de cadastro — canto superior direito

**Problema atual:** posição inconsistente do "Cadastrado em" entre os containers:
- Endereços: aparece no rodapé do item (dentro do `flex justify-between` final)
- Veículos: aparece à direita no meio do conteúdo
- Abordagens: `criado_em` não é exibido

**Design:**
Todos os containers de item terão uma **linha de topo** com `flex justify-between`:
- Esquerda: info principal (endereço formatado, placa, `#id da abordagem`)
- Direita: `"Cadastrado em dd/mm/aaaa"` em `text-xs text-slate-500`

O conteúdo secundário (modelo/cor do veículo, bairro, observação) fica abaixo dessa linha.

---

## 2. Histórico de abordagens — campo "Cadastrada em"

**Problema atual:** exibe apenas `ab.data_hora` (momento da abordagem) sem label. `ab.criado_em` não é exibido.

**Design:**

```
┌─────────────────────────────────────────────────────┐
│ #42 · Data da Abordagem: 21/06/2024 14:35           │  ← esquerda
│                          Cadastrada em 21/06/2024 às 14:35 │  ← direita
│ Endereço da Abordagem: Rua X, Centro                │
│ Observação: ...                                     │
└─────────────────────────────────────────────────────┘
```

- `ab.data_hora` → label "Data da Abordagem:" (permanece, esquerda)
- `ab.criado_em` → label "Cadastrada em dd/mm/aaaa às HH:MM" (canto superior direito, `text-xs text-slate-500`)
- Se `ab.criado_em` não vier do backend, ocultar com `x-show`

---

## 3. Sistema de cores cíclicas

### Paleta (8 cores, full class strings para compatibilidade com Tailwind purge)

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

### Cards de seção (borda fixa por grupo)

| Seção       | Classe atual         | Classe nova            |
|-------------|----------------------|------------------------|
| Endereços   | sem borda no card    | `border-l-blue-600`    |
| Veículos    | sem borda no card    | `border-l-green-600`   |
| Abordagens  | sem borda no card    | `border-l-purple-600`  |

### Itens individuais (ciclam pela paleta)

Usar `x-for="(item, idx) in lista"` e `:class="PALETTE[idx % PALETTE.length]"`.

Exemplo para endereços:
```html
<template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
  <div :class="'border border-slate-700/40 border-l-4 rounded-lg p-3 ' + PALETTE[idx % PALETTE.length]">
    ...
  </div>
</template>
```

A paleta é compartilhada entre as seções (cada seção reinicia o índice do seu próprio loop).

---

## Arquivos a modificar

| Arquivo | Mudanças |
|---------|----------|
| `frontend/js/pages/pessoa-detalhe.js` | Tudo: paleta, cores, layout, criado_em |

Nenhuma mudança de backend necessária — `criado_em` já existe via `TimestampMixin`.

---

## Abordagem escolhida

**A — Localizado em `pessoa-detalhe.js`**
- Paleta como constante JS no topo do arquivo
- Alpine `x-for` com índice `(item, idx)`
- Sem helpers globais, sem classes CSS customizadas
