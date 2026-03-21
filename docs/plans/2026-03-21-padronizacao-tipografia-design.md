# Padronização Tipográfica e Espaçamentos — Design

**Data:** 2026-03-21
**Status:** Aprovado

## Contexto

O sistema tem inconsistências tipográficas entre páginas:
- `perfil.js` e `ocorrencia-upload.js` usam unidades `rem` em estilos inline
- O CSS global define `input { padding: 10px 14px }` mas a página de referência (consulta) usa `12px` verticalmente via override inline
- Fontes e tamanhos divergem entre páginas

## Padrão de Referência (consulta.js)

| Elemento | Font | Tamanho | Cor | Modificadores |
|---|---|---|---|---|
| Título de página (h2) | `font-display` | `18px` | `text` | uppercase, `letter-spacing: 0.08em`, `weight: 700` |
| Subtítulo de página | `font-data` | `12px` | `text-dim` | uppercase, `letter-spacing: 0.1em` |
| Header de seção (card) | `font-display` | `12px` | `text-muted` | uppercase, `letter-spacing: 0.08em`, `weight: 500` |
| Label de campo | `font-body` | `11px` | `text-muted` | uppercase, `letter-spacing: 0.1em` |
| Input / Select / Textarea | `font-body` | `14px` | `text` | `padding: 12px 14px` |
| Texto secundário/helper | `font-data` | `11px` | `text-dim` | uppercase |
| Texto de resultados/itens | `font-body` | `14px` | `text` | — |
| Tags/badges pequenos | `font-data` | `12px` | `primary` | — |

## Mudanças por Arquivo

### 1. `frontend/css/app.css`

Bloco `input, textarea, select`: alterar `padding: 10px 14px` → `padding: 12px 14px`.

Isso propaga automaticamente para todos os campos do sistema.

### 2. `frontend/js/pages/perfil.js`

Converter unidades `rem` para `px` equivalentes (1rem = 16px base):

| De | Para |
|---|---|
| `padding: 1rem` | `padding: 16px` |
| `gap: 1rem` | `gap: 16px` |
| `gap: 1.5rem` | `gap: 24px` |
| `margin-bottom: 1.5rem` | `margin-bottom: 24px` |
| `margin-top: 2rem` | `margin-top: 32px` |
| `padding-top: 1.5rem` | `padding-top: 24px` |
| `margin-top: 0.5rem` | `margin-top: 8px` |
| `margin-top: 0.25rem` | `margin-top: 4px` |
| `font-size: 1.875rem` (avatar iniciais) | `font-size: 28px` |
| `font-size: 0.875rem` (botão sair, textos) | `font-size: 14px` |
| `font-size: 0.75rem` (upload status) | `font-size: 12px` |
| `max-width: 28rem` | `max-width: 448px` |
| `padding: 0.5rem 1rem` (botão sair) | `padding: 8px 16px` |

### 3. `frontend/js/pages/ocorrencia-upload.js`

| De | Para |
|---|---|
| `font-size:1.25rem` (título h2) | `font-size:18px` |
| `font-size:0.7rem` (subtítulo) | `font-size:12px` |
| `font-size:0.85rem` (section header) | `font-size:12px` |
| `font-size:0.875rem` (success/error, textos) | `font-size:14px` |
| `font-size:0.75rem` (tags envolvidos) | `font-size:12px` |
| `font-size:0.875rem` (botão × em tags) | `font-size:14px` |

### 4. `frontend/js/pages/consulta.js`

Remover overrides inline redundantes no input principal de busca de pessoa:
- `padding-top:12px;padding-bottom:12px;` → removidos (CSS global cobre)
- `font-size:14px;` → removido (CSS global cobre)

## Arquivos Afetados

| Arquivo | Tipo de mudança |
|---|---|
| `frontend/css/app.css` | input padding 10px → 12px |
| `frontend/js/pages/perfil.js` | rem → px em todos os estilos inline |
| `frontend/js/pages/ocorrencia-upload.js` | rem → px nos font-sizes |
| `frontend/js/pages/consulta.js` | remover overrides inline redundantes |
