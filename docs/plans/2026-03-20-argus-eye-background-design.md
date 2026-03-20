# Design: Argus Eye — Background Visual

**Data:** 2026-03-20
**Status:** Aprovado

## Objetivo

Usar a imagem do olho cibernético como papel de fundo do sistema, ornando com a estética cyberpunk tática já existente (fundo `#050A0F`, grid ciano, scan lines).

## Comportamento

- **Login:** imagem visível em opacidade `0.45`, com vinheta nas bordas concentrando o foco no olho central
- **Sistema (demais páginas):** imagem sutil em opacidade `0.18`, atrás de todo o conteúdo
- **Transição:** `opacity 0.6s ease` — fade suave ao navegar entre login e sistema

## Abordagem Escolhida

Elemento `<img>` fixo no DOM, controlado via Alpine.js. Escolhida por oferecer controle de opacidade reativo por rota sem complexidade de Canvas.

## Arquitetura

### Elemento no DOM (`index.html`)

```html
<img id="argus-eye-bg"
     src="/images/argus-eye.jpg"
     :style="{ opacity: currentPage === 'login' ? '0.45' : '0.18' }"
     alt="">
```

Inserido logo após `<body>`, antes de qualquer outro elemento.

### CSS (`app.css`)

```css
#argus-eye-bg {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  z-index: -1;
  pointer-events: none;
  mix-blend-mode: luminosity;
  transition: opacity 0.6s ease;
}

/* Vinheta ativa no login */
body.login-active::before {
  /* sobrepõe radial-gradient escurecendo bordas */
  background-image:
    radial-gradient(ellipse at center, transparent 30%, rgba(5,10,15,0.85) 80%),
    linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
}
```

### Controle de rota (Alpine.js)

`currentPage` já existe em `app()` e é reativo ao hash. Sem variáveis novas.
A classe `login-active` é adicionada ao `body` quando `currentPage === 'login'` via `:class`.

## Arquivos Modificados

| Arquivo | Mudança |
|---|---|
| `frontend/images/argus-eye.jpg` | Imagem adicionada |
| `frontend/index.html` | `<img #argus-eye-bg>` + `:class` no body + bump de versão CSS |
| `frontend/css/app.css` | Estilos do `#argus-eye-bg` + `.login-active::before` |

## Restrições

- `z-index: -1` — fica abaixo do grid (`z-index: 0`) e scan lines (`z-index: 1`)
- `mix-blend-mode: luminosity` — cores da imagem fundem com o tema, sem vermelho/branco
- `pointer-events: none` — nunca intercepta interação do usuário
- Nenhum componente de página precisa ser alterado
