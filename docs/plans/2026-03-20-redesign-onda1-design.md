# Redesign Onda 1 — Fundação Visual Cyberpunk Tático

**Data:** 2026-03-20
**Escopo:** Sistema de design + Sidebar + Login + Header
**Estratégia:** Redesign in-place (manter arquitetura Alpine.js + Tailwind CDN)

## 1. Sistema de Design (CSS Variables + Tipografia + Efeitos)

### Paleta
```css
--color-bg:            #050A0F
--color-surface:       #0D1520
--color-surface-hover: #1A2940
--color-border:        #1A2940
--color-text:          #E8F4FF
--color-text-muted:    #6B8FA8
--color-primary:       #00D4FF
--color-primary-hover: #00B8E0
--color-success:       #00FF88
--color-danger:        #FF6B00
--color-warning:       #FF6B00
```

### Tipografia (Google Fonts CDN)
- Títulos: JetBrains Mono 700
- Corpo: IBM Plex Sans 400/500
- Dados/métricas: Rajdhani 600

### Efeitos Globais
- Scan line overlay (::after no body, pointer-events: none)
- Grid de fundo sutil (linear-gradients finos)
- `.glow-cyan` — box-shadow com --color-primary
- Pulse animation para status dots
- `.glass-card` — backdrop-blur + borda ciano translúcida
- border-radius máximo: 4px
- Transições globais: 150ms

## 2. Sidebar Colapsável

Substituir bottom-nav por sidebar lateral esquerda.

- Expandida: ícone + label (240px)
- Colapsada: só ícone (64px)
- Mobile: overlay com backdrop, toggle via hamburger no header
- Itens: Dashboard, Ocorrências, Consulta IA, Reconhecimento, Relatórios, Mapa, Configurações
- Rodapé: avatar + nome + nível de acesso
- Linha de status: API/IA/DB com dots pulsantes
- Badges de contagem nos itens
- Ícones: Lucide Icons (CDN)

## 3. Login Redesenhado

- Background #050A0F com grid lines
- Scan line overlay ativo
- Logo "ARGUS" em JetBrains Mono com glow ciano
- Subtítulo "SISTEMA DE INTELIGÊNCIA OPERACIONAL" em Rajdhani
- Campos com borda animada (→ ciano ao focar)
- Labels uppercase com letter-spacing
- Status dot pulsante (ONLINE/OFFLINE)
- Botão ciano com glow no hover
- Versão em estilo terminal: v1.0.0 // PMDF

## 4. Header Fixo

Substituir header atual.

- Fundo #0D1520 com borda inferior #1A2940
- Esquerda: hamburger (mobile) + "ARGUS" com glow
- Centro: mini barra de busca IA
- Direita: ID operador | Guarnição | Turno | Relógio HH:MM:SS | Status sync

## Ondas Futuras (fora do escopo)

- **Onda 2:** Dashboard principal + Card de ocorrência + Barra de busca IA
- **Onda 3:** Registro de ocorrência + Consulta RAG + Reconhecimento facial
