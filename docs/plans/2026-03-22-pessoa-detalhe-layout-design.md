# Design: Melhorias de Layout — Página Pessoa Detalhe

**Data:** 2026-03-22
**Arquivo alvo:** `frontend/js/pages/pessoa-detalhe.js`, `frontend/css/app.css`

## Problema

A página de detalhe de pessoa (`#pessoa-detalhe`) apresenta vários problemas de legibilidade:
- Textos colados nas bordas dos containers (padding irregular/insuficiente)
- Containers filhos grudados aos pais sem espaçamento entre níveis
- Borda esquerda dos containers sem padrão visual consistente
- Thumbnails de fotos e veículos em tamanhos inconsistentes
- Foto de abordado no grid muito grande
- Botão "+ Adicionar" de vínculo grande demais (btn-primary), domina visualmente

## Abordagem Escolhida

**Classes CSS globais** — duas novas classes em `app.css` + ajustes inline no JS.

## Design

### 1. Sistema de LED — `app.css`

Duas classes novas após `.glass-card`:

```css
.card-led-blue {
  border-left: 3px solid #00D4FF;
  animation: led-pulse-blue 2.5s ease-in-out infinite;
}
@keyframes led-pulse-blue {
  0%, 100% { box-shadow: -3px 0 8px rgba(0, 212, 255, 0.4); }
  50%       { box-shadow: -3px 0 14px rgba(0, 212, 255, 0.8), -1px 0 4px rgba(0, 212, 255, 0.3); }
}

.card-led-purple {
  border-left: 3px solid #A78BFA;
  animation: led-pulse-purple 2.5s ease-in-out infinite;
}
@keyframes led-pulse-purple {
  0%, 100% { box-shadow: -3px 0 8px rgba(167, 139, 250, 0.35); }
  50%       { box-shadow: -3px 0 14px rgba(167, 139, 250, 0.7), -1px 0 4px rgba(167, 139, 250, 0.25); }
}
```

**Uso:**
- Containers pai (`glass-card` nível 1): adicionar classe `card-led-blue` + remover `border-left` inline
- Cards filhos (endereços, veículos, abordagens, vínculos individuais): adicionar classe `card-led-purple` + remover `border-left` inline (incluindo os do `PALETTE`)

### 2. Padding e espaçamento — `pessoa-detalhe.js`

- `glass-card`: padding interno `1rem` consistente em todos
- Gap interno dos glass-card: `0.75rem`
- Cards filhos (itens dentro dos glass-cards): `padding: 0.75rem`, gap entre eles `0.5rem`
- Rótulos de seção (`h3`): adicionar `padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border)` para separar título do conteúdo

### 3. Thumbnails padronizadas

| Contexto | Tamanho atual | Novo |
|---|---|---|
| Fotos grid (abordado) | `width: 100%; height: 7rem` | `height: 5rem` |
| Thumbnail veículo | `4rem × 4rem` | `3.5rem × 3.5rem` |
| Avatar vínculos/coabordados | `2rem × 2rem` | `2.5rem × 2.5rem` |
| Avatar busca de vínculo | `1.75rem × 1.75rem` | `2rem × 2rem` |

### 4. Botão Adicionar Vínculo

Remover `<button class="btn btn-primary">` e substituir por link de texto discreto no canto superior direito do container de vínculos:

```html
<button style="background: none; border: none; cursor: pointer;
               color: var(--color-primary); font-size: 0.75rem;
               font-family: var(--font-data); font-weight: 600;
               letter-spacing: 0.05em; padding: 0;">
  + Adicionar Vínculo
</button>
```

### 5. Melhorias adicionais

- **Badge "Atual"** do endereço: substituir texto colorido por badge `background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); padding: 0 0.375rem; border-radius: 2px`
- **Placa do veículo**: fundo destacado `background: var(--color-surface-hover); padding: 0.125rem 0.375rem; border-radius: 2px`

## Arquivos Modificados

1. `frontend/css/app.css` — adicionar `.card-led-blue`, `.card-led-purple` e keyframes
2. `frontend/js/pages/pessoa-detalhe.js` — padding, gap, thumbnails, botão, badges
