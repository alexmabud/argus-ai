# Design: Consulta — Ver Mais completo + Zoom de foto

**Data:** 2026-03-28
**Arquivo principal:** `frontend/js/pages/consulta.js`

---

## Contexto

A página de consulta (`consulta.js`) lista até 10 resultados inicialmente e exibe botão "ver mais" quando há mais. O modal "ver mais" mostrava apenas os mesmos 20 resultados já carregados (limite padrão da API), não todos os cadastros. Além disso, não havia interação de zoom nas fotos.

---

## Fix 1 — Ver Mais busca todos os registros

### Problema
A API `/consultas/` usa `limit=20` por padrão. O frontend não passa `limit` explícito, então recebe 20 resultados. O modal "ver mais" renderiza `pessoasTexto` (já limitado a 20) sem buscar mais.

### Solução
Ao abrir qualquer modal "ver mais", disparar uma nova chamada à API com `limit=100` (máximo permitido pelo backend, definido em `consultas.py` como `le=100`).

**Comportamento:**
- Estado `loadingVerMais: false` adicionado ao componente Alpine
- Ao `@click` do botão "ver mais": setar `modalVerMaisTexto = true` + chamar `carregarTodosTexto()`
- `carregarTodosTexto()`: busca `/consultas/?q=...&tipo=pessoa&limit=100`, atualiza `pessoasTexto`
- Modal exibe spinner enquanto `loadingVerMais` for true
- Mesma lógica para Endereço (`carregarTodosEndereco`) e Veículo (`carregarTodosVeiculo`)

---

## Fix 2 — Press & hold para zoom de foto (lista inicial)

### Comportamento
- Na lista inicial (10 itens), cada avatar 32×32px:
  - **Press & hold (>200ms):** exibe overlay fullscreen com foto ampliada (~80vw)
  - **Soltar / mover fora:** fecha overlay
  - **Click rápido (<200ms):** navega para ficha (comportamento existente)

### Implementação
- Estado global no componente: `zoomFoto: { url: '', nome: '' }, zoomFotoVisible: false`
- Funções: `iniciarZoom(url, nome)` — seta timer 200ms, `cancelarZoom()` — limpa timer e fecha overlay
- Eventos na `<img>` e no placeholder SVG:
  - `@pointerdown="iniciarZoom(p.foto_principal_url, p.nome)"`
  - `@pointerup="cancelarZoom()" @pointerleave="cancelarZoom()"`
- O `@click` existente no `<div>` pai chama `viewPessoa` — permanece sem alteração
- Overlay: `position:fixed; inset:0; z-index:100; background:rgba(0,0,0,0.9)` com `<img>` centralizada `max-width:80vw; max-height:80vh`

---

## Fix 3 — Press & hold + click no modal "Ver Mais"

### Comportamento
- No grid 4 colunas do modal:
  - **Press & hold (>200ms):** zoom na foto (mesmo overlay do Fix 2)
  - **Click rápido (<200ms):** fecha modal + navega para ficha

### Implementação
- Substituir `@click` nos itens do modal por `@pointerdown` / `@pointerup` com lógica de timer
- Reusar o mesmo mecanismo `iniciarZoom` / `cancelarZoom` do Fix 2
- No `pointerup` rápido: executar `modalVerMaisTexto = false; viewPessoa(p.id)`
- Aplica-se aos 3 modais (texto, endereço, veículo)

---

## Overlay de Zoom (compartilhado)

Um único overlay no HTML, fora dos modais:

```html
<div x-show="zoomFotoVisible" @click="zoomFotoVisible = false"
     style="position:fixed;inset:0;z-index:100;background:rgba(0,0,0,0.92);
            display:flex;align-items:center;justify-content:center;">
  <img :src="zoomFoto.url" :alt="zoomFoto.nome"
       style="max-width:80vw;max-height:80vh;border-radius:4px;object-fit:contain;">
</div>
```

---

## Arquivos alterados

| Arquivo | Mudanças |
|---|---|
| `frontend/js/pages/consulta.js` | Todos os fixes (único arquivo) |

---

## Sem mudanças necessárias no backend

O backend já suporta `limit=100` via query param. Nenhuma alteração em Python.
