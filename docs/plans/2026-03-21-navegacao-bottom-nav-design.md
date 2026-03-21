# Design — Nova Navegação Argus AI

**Data:** 2026-03-21
**Status:** Aprovado

## Contexto

O sistema atual usa uma sidebar lateral para navegação. O objetivo é substituí-la por um padrão mais adequado para PWA mobile: bottom navigation bar, com header simplificado.

## Decisões

- Bottom nav aparece **apenas em subpáginas** (não na home) — Opção B escolhida pelo usuário
- Botão voltar no header **desaparece** na home (não fica vazio nem muda de ícone)
- Layout único para browser e app mobile (sem comportamento diferenciado)

## 1. Remoção da Sidebar

- Remover `<aside class="sidebar">`, `sidebar-overlay`, e todo HTML da sidebar do `index.html`
- Remover `sidebarComponent()` de `sidebar.js` (arquivo pode ser removido)
- Remover estilos `.sidebar`, `.sidebar-*`, `.sidebar-overlay` do `app.css`
- `app-main` perde `margin-left` — passa a ocupar largura total

## 2. Header Reformulado

Layout das zonas (esquerda → direita):

```
[ ← voltar ]  [ ARGUS ]  [ search bar ]  [ • API  • IA  • DB ]  [ 👤 avatar ]
```

### Botão Voltar
- Visível apenas quando `currentPage !== 'home'`
- Clica → `navigate('home')`
- Na home: `display:none` (não ocupa espaço)

### LEDs de Status (API · IA · DB)
- Migram do footer da sidebar para o header
- Posição: à esquerda do avatar do usuário
- Visual: mesmo estilo dos dots atuais (`status-dot`)

### Avatar do Usuário
- Posição: canto superior direito do header
- Visual: mesmo `sidebar-user-avatar` atual (foto ou iniciais)
- Clique: navega para `perfil`

## 3. Bottom Navigation Bar

### Quando aparece
Apenas quando `currentPage !== 'home'`. Controlado via Alpine.js com `x-show`.

### Visual
```css
background: rgba(5, 10, 15, 0.55);
backdrop-filter: blur(16px);
border-top: 1px solid rgba(0, 212, 255, 0.12);
box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.6);
height: 64px;
position: fixed;
bottom: 0;
left: 0;
right: 0;
z-index: 150;
```

### Botões (5, espaçados igualmente)
| Posição | Ícone | Label | Página |
|---|---|---|---|
| 1 | `plus-circle` | Nova Abordagem | `abordagem-nova` |
| 2 | `search` | Consulta IA | `consulta` |
| 3 | `home` | Início | `home` |
| 4 | `file-up` | Ocorrência | `ocorrencia-upload` |
| 5 | `bar-chart-3` | Analítico | `dashboard` |

### Estados dos botões
- **Normal:** `color: var(--color-text-muted)`
- **Ativo** (página atual): `color: var(--color-primary)` + `filter: drop-shadow(0 0 6px rgba(0,212,255,0.6))`
- **Hover/tap:** `transform: scale(1.08)` + glow fraco

### Label
- Fonte: `var(--font-data)`, 10px, uppercase
- Visível abaixo do ícone

## 4. Padding no app-main

Quando bottom nav está visível (`currentPage !== 'home'`), `app-main` recebe `padding-bottom: 80px` para o conteúdo não ficar atrás do nav.

Implementado via classe Alpine: `:class="{ 'has-bottom-nav': currentPage !== 'home' }"`.

## Arquivos Afetados

| Arquivo | Mudança |
|---|---|
| `frontend/index.html` | Remove sidebar, reformula header, adiciona bottom nav |
| `frontend/css/app.css` | Remove estilos sidebar, adiciona `.bottom-nav`, ajusta `.app-main` |
| `frontend/js/components/sidebar.js` | Remover arquivo |
| `frontend/js/app.js` | Remove dependência sidebarComponent, adiciona ícones do bottom nav |
