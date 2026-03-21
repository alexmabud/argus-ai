# Design: Modernização dos Cards de Ação da Home

**Data:** 2026-03-21
**Escopo:** `frontend/js/app.js` · `frontend/css/app.css`
**Status:** Aprovado

---

## Contexto

A tela inicial (`renderHomePage`) exibe 4 botões em grid 2x2 para navegação rápida:

| Botão | Destino | Código tático |
|---|---|---|
| Nova Abordagem | `abordagem-nova` | `// ABD` |
| Consulta IA | `consulta` | `// IA` |
| Ocorrência | `ocorrencia-upload` | `// OCR` |
| Analítico | `dashboard` | `// ANL` |

Atualmente são cards genéricos (classe `.card .card-interactive`) — mesma aparência, hover quase imperceptível, sem profundidade visual.

---

## Decisões de Design

- **Paleta:** monocromático cyan (`#00D4FF`) — sem cores distintas por botão
- **4 cards visualmente equivalentes** — sem hierarquia de destaque
- **Estilo:** mix de glassmorphism premium + HUD tático militar

---

## Estrutura Visual — `.home-action-card`

```
┌─────────────────────┐  ← borda cyan 1px, opacity 0.15
│ // ABD           ◆  │  ← código tático + dot (JetBrains Mono 9px, dim)
│                     │
│      [ícone 32px]   │  ← glow drop-shadow sutil
│                     │
│   NOVA ABORDAGEM    │  ← Rajdhani 13px, uppercase, muted
└─────────────────────┘ ↗ clip-path: canto inferior-direito cortado 12px
```

### Fundo e borda
- `background: rgba(13, 21, 32, 0.75)` + `backdrop-filter: blur(12px)`
- `border: 1px solid rgba(0, 212, 255, 0.15)` em repouso
- `clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%)`

### Cabeçalho interno
- Código tático (`// ABD` etc.) — JetBrains Mono 9px, `var(--color-text-dim)`, canto superior esquerdo
- Dot decorativo (`◆`) — canto superior direito, mesma cor

### Ícone
- SVG 32px centralizado
- `filter: drop-shadow(0 0 4px rgba(0, 212, 255, 0.35))` — glow sutil sempre presente

### Label
- Rajdhani 13px, uppercase, `var(--color-text-muted)`

---

## Estados de Interação

| Estado | Efeito |
|---|---|
| **Repouso** | borda dim, ícone com glow leve |
| **Hover** | borda → `rgba(0,212,255,0.5)`, `box-shadow` glow externo+interno, scan line desce, ícone intensifica, `translateY(-2px)` |
| **Active** | `translateY(0)` — retorna ao lugar |

### Scan line no hover
Pseudo-elemento `::after` com `linear-gradient(transparent, rgba(0,212,255,0.08), transparent)` animado de cima para baixo em 0.4s ease quando `:hover`.

---

## Animação de Entrada (stagger)

Ao renderizar a home, os cards entram em sequência:

| Card | Delay |
|---|---|
| Nova Abordagem | 0ms |
| Consulta IA | 60ms |
| Ocorrência | 120ms |
| Analítico | 180ms |

Keyframe: `opacity: 0 + translateY(8px)` → `opacity: 1 + translateY(0)` em 250ms ease-out.

---

## Implementação

### Arquivos a modificar
1. **`frontend/css/app.css`** — adicionar classe `.home-action-card` com todos os estilos, keyframe `card-enter`, pseudo-elementos
2. **`frontend/js/app.js`** — atualizar `renderHomePage()`: trocar `.card.card-interactive` por `.home-action-card`, adicionar cabeçalho com código tático e dot decorativo, aplicar `animation-delay` por card

### Sem dependências novas
CSS puro + atualização de HTML gerado. Nenhuma biblioteca adicional.
