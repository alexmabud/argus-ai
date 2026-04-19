# Design: Modal Bloqueante de Perfil Incompleto

**Data:** 2026-04-19
**Status:** Aprovado

## Problema

Usuários comuns são cadastrados pelo admin apenas com matrícula. Os campos `nome`, `posto_graduacao` e `nome_guerra` ficam vazios, e os usuários não completam o perfil voluntariamente. Isso prejudica a identificação nos registros de abordagem.

## Solução

Modal fullscreen bloqueante exibido automaticamente quando o usuário abre o sistema com perfil incompleto. O sistema só libera o acesso após o preenchimento de todos os campos obrigatórios.

## Escopo

- **Usuários afetados:** apenas usuários comuns (`is_admin === false`)
- **Campos obrigatórios:** `nome`, `posto_graduacao`, `nome_guerra`
- **Backend:** nenhuma mudança — reutiliza o endpoint `/auth/perfil` existente
- **Frontend:** apenas `frontend/js/app.js`

## Lógica de Verificação

```js
_perfilIncompleto(user) {
  if (!user || user.is_admin) return false;
  return !user.nome?.trim() || !user.posto_graduacao || !user.nome_guerra?.trim();
}
```

## Pontos de Disparo

| Onde | Quando |
|------|--------|
| `onLogin(user)` | Logo após login bem-sucedido |
| `init()` | Quando app abre com sessão existente no localStorage |

Em ambos os casos: navega para home normalmente, depois exibe o modal por cima.

## Comportamento do Modal

- Overlay `position:fixed; inset:0; z-index:9999` — cobre tudo, inescapável
- Sem botão de fechar
- Campos: Nome completo, Nome de guerra, Posto/Graduação (select)
- Botão "Salvar e continuar" desabilitado enquanto salva
- Ao salvar com sucesso:
  1. Remove o overlay do DOM
  2. Atualiza `auth.user` e localStorage
  3. Dispara `user:updated` (app já escuta e atualiza `this.user`)
  4. Exibe toast de sucesso

## Implementação

### Padrão seguido

Mesmo padrão de `mostrarModalSaida()` em `perfil.js`: criação dinâmica de elemento DOM + `Alpine.initTree()`.

### Funções adicionadas em `app.js`

1. `_perfilIncompleto(user)` — helper de verificação
2. `_mostrarModalCompletarPerfil()` — cria e injeta o overlay no body
3. `completarPerfilModal()` — componente Alpine do formulário dentro do modal

### Calls existentes modificadas

- `onLogin(user)`: adiciona check após `this.user = user`
- `init()`: adiciona check após `this.user = auth.getUser()`

## Performance

- Verificação: O(1) — três comparações de string, nenhuma chamada de rede
- Modal: criado apenas quando necessário, destruído após uso
- Nenhum impact no carregamento normal do app

## Arquivos Alterados

```
frontend/js/app.js   — único arquivo modificado
```
