# Design System — Containers e Legendas de Foto na Consulta de Pessoa

## Objetivo

Padronizar a página de detalhe de pessoa (`pessoa-detalhe.js`) com um design system consistente:
1. Cada item das seções de lista (endereços, veículos, abordagens) em container próprio com borda colorida lateral
2. Seções de bloco único (dados pessoais, fotos, fotos de veículos) com borda colorida no card da seção
3. Legenda de data abaixo de cada foto (abordado e veículo)

## Arquitetura

Todas as mudanças são exclusivamente em `frontend/js/pages/pessoa-detalhe.js`.
Nenhuma alteração de backend, API ou schema necessária.

## Stack

Alpine.js, Tailwind CSS, Vanilla JS.

## Design System

### Regra geral

**Seções com conteúdo único** (sem itens repetidos): o card da seção recebe a borda colorida.
**Seções com lista de itens**: cada item recebe seu próprio container com borda colorida.

### Estrutura CSS base de cada container/card

```
border border-slate-700/40 border-l-4 border-l-[cor] rounded-lg p-3
```

### Mapeamento de cores por seção

| Seção | Nível | Classe Tailwind |
|---|---|---|
| Dados Pessoais | card da seção | `border-l-slate-400` |
| Fotos (abordado) | card da seção | `border-l-amber-500` |
| Fotos de Veículos | card da seção | `border-l-teal-500` |
| Endereços | cada item | `border-l-blue-500` |
| Veículos vinculados | cada item | `border-l-green-500` |
| Vínculos (relacionamentos) | cada item | `border-l-orange-500` |
| Histórico de Abordagens | cada item | `border-l-purple-500` |

### Legenda de data nas fotos

Cada foto (abordado e veículo) passa a exibir a data de cadastro como legenda abaixo da imagem:

```html
<div>
  <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy" ...>
  <p class="text-xs text-slate-400 text-center mt-1"
     x-text="new Date(foto.criado_em).toLocaleDateString('pt-BR')"></p>
</div>
```

O badge de tipo (`veiculo`, `placa`, `foto`) permanece como overlay na imagem.

## Seções afetadas em detalhe

### Dados Pessoais
- Substituir `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-slate-400"`

### Fotos (abordado)
- Substituir `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-amber-500"`
- Adicionar `<p>` com data abaixo de cada `<img>`

### Fotos de Veículos
- Substituir `class="card space-y-2"` por `class="card space-y-2 border-l-4 border-l-teal-500"`
- Adicionar `<p>` com data abaixo de cada `<img>`

### Endereços (cada item)
- Substituir `class="border-l-2 pl-3 py-1"` por container completo:
  `class="border border-slate-700/40 border-l-4 border-l-blue-500 rounded-lg p-3"`

### Veículos vinculados (cada item)
- Substituir `class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2"` por:
  `class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-green-500 rounded-lg p-3"`

### Vínculos / Relacionamentos (cada item)
- Substituir `class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2 cursor-pointer hover:bg-slate-700/50"` por:
  `class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-orange-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50"`

### Histórico de Abordagens (cada item)
- Substituir `class="border border-slate-700 rounded-lg p-3 space-y-2"` por:
  `class="border border-slate-700/40 border-l-4 border-l-purple-500 rounded-lg p-3 space-y-2"`

## Arquivo modificado

| Arquivo | Mudanças |
|---|---|
| `frontend/js/pages/pessoa-detalhe.js` | Classes CSS em todos os containers/cards + legenda de data nas fotos |

## Verificação final

Após implementação, verificar no app:
1. Dados Pessoais com borda esquerda cinza
2. Fotos do abordado com borda âmbar e data abaixo de cada foto
3. Cada endereço em container próprio com borda azul
4. Cada veículo em container com borda verde
5. Fotos de veículos com borda teal e data abaixo de cada foto
6. Cada vínculo com borda laranja
7. Cada abordagem com borda roxa
