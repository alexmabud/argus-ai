# Design: Bottom Nav "Tactical Pulse"

**Data:** 2026-03-21
**Escopo:** Redesign visual dos botões do bottom navigation (Abordagem, Consulta IA, Início, Ocorrência, Analítico)

## Objetivo

Tornar todos os botões do bottom nav mais atraentes, combinando três direções:
- **Neon/glow** — ícones com brilho ciano sempre presente, intensificando nos estados
- **Estruturado** — pill (cápsula) como fundo visível de cada botão
- **Animado** — barra indicadora pulsando no ativo, transições suaves em todos os estados

## Design

### Estrutura HTML (por botão)

Cada `.bottom-nav-btn` passa a ter internamente:
1. **Barra indicadora** — `div.nav-indicator` absolutamente posicionada no topo da pill
2. **Ícone SVG** — 24px (era 22px)
3. **Label** — mantida, levemente maior

### Estados dos botões

| Estado | Pill background | Pill border | Ícone | Label | Transform |
|--------|----------------|-------------|-------|-------|-----------|
| Repouso | transparente | none | `color-text-dim`, glow mínimo | dim | nenhum |
| Hover | `rgba(0,212,255,0.08)` | `rgba(0,212,255,0.15)` | `color-text-muted`, glow médio | muted | `scale(1.06)` |
| Ativo | `rgba(0,212,255,0.12)` | `rgba(0,212,255,0.25)` | `color-primary`, glow forte | ciano | nenhum |

### Barra indicadora (`.nav-indicator`)

- Posição: topo da pill, centralizada
- Tamanho: `40px × 2px`
- Cor: `var(--color-primary)` sólido
- Border-radius: `0 0 2px 2px`
- Visível apenas no botão ativo (`opacity: 0` → `opacity: 1`)
- Animação: `pulse-glow` já existente no CSS, `2s infinite`
- Box-shadow: `0 0 8px rgba(0,212,255,0.8)`

### Pill (wrapper interno)

- Border-radius: `10px`
- Padding: `6px 14px 4px`
- Border: `1px solid transparent` → visível no hover/ativo
- Transition: `all 200ms ease`
- Contém: indicador + ícone + label em coluna

### Ícones

- Tamanho: `24px × 24px` (era 22px)
- `filter: drop-shadow(0 0 3px rgba(0,212,255,0.2))` em repouso
- `filter: drop-shadow(0 0 6px rgba(0,212,255,0.5))` no hover
- `filter: drop-shadow(0 0 10px rgba(0,212,255,0.8))` no ativo

### Label

- Font-size: `10px` (mantida)
- Transition: `color 200ms ease`

## Arquivos a modificar

1. **`frontend/css/app.css`** — atualizar `.bottom-nav-btn`, `.bottom-nav-btn:hover`, `.bottom-nav-btn.active`, `.bottom-nav-btn svg`, `.bottom-nav-label`; adicionar `.nav-pill` e `.nav-indicator`
2. **`frontend/index.html`** — adicionar estrutura interna da pill + indicador em cada botão; bump de versão dos scripts

## Restrições

- Manter o fundo do nav (semi-transparente + blur) intacto
- Não alterar layout (5 botões, `space-around`)
- Compatível com o sistema de design cyberpunk/tático existente
- Sem dependências externas novas
