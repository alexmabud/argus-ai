# Design: Perfil do Usuário e Gestão de Acesso

**Data:** 2026-03-16
**Status:** Aprovado

---

## Contexto

O app atualmente tem um botão "Sair" simples no header. Não existe tela de perfil nem gestão de usuários. Qualquer pessoa com uma matrícula e senha poderia tentar acessar o sistema. Este design adiciona duas funcionalidades:

1. **Perfil do usuário** — cada policial configura nome, posto/graduação e foto
2. **Gestão de acesso** — admin controla quem entra no sistema com modelo de senha única

---

## Feature 1 — Perfil do Usuário

### UI

**Header:**
- Botão "Sair" é removido
- Substituído por avatar circular (foto do usuário, ou iniciais do nome caso sem foto)
- Clicar no avatar abre a tela de perfil

**Tela de perfil:**
- Foto grande com botão para trocar (upload para R2)
- Nome completo (editável)
- Posto/graduação (dropdown fixo — ver lista abaixo)
- Matrícula (somente leitura)
- Botão "Salvar alterações"
- Botão "Sair" com modal de confirmação:
  > "Se você sair, precisará que o admin gere uma nova senha para acessar novamente. Deseja continuar?"

**Lista fixa de postos/graduações (PM):**
Soldado, Cabo, 3º Sargento, 2º Sargento, 1º Sargento, Subtenente, Aspirante, 2º Tenente, 1º Tenente, Capitão, Major, Tenente-Coronel, Coronel

### Backend

**Alterações no model `Usuario`:**
- `posto_graduacao: str | None` — enum string (lista fixa validada no schema)
- `foto_url: str | None` — URL pública no R2
- `session_id: str | None` — UUID de sessão ativa (ver Seção 2)

**Novos endpoints:**
- `PUT /auth/perfil` — atualiza nome, posto_graduacao, foto_url
- `POST /auth/perfil/foto` — upload de foto para R2, retorna URL

**Schema `UsuarioRead` atualizado:**
- Incluir `posto_graduacao` e `foto_url`

---

## Feature 2 — Segurança de Sessão (Senha Única + Sessão Exclusiva)

### Modelo de senha única

1. Admin cria usuário informando apenas a matrícula
2. Sistema gera senha aleatória segura (8 caracteres, letras + números)
3. Senha é exibida **uma única vez** na tela do admin (não é armazenada em plain text)
4. Sistema salva o bcrypt hash da senha no campo `senha_hash`
5. Usuário faz login com matrícula + senha gerada
6. **Após login bem-sucedido:** sistema substitui `senha_hash` por hash de UUID aleatório — a senha nunca mais funciona
7. Tentativas de reuso da mesma senha → acesso negado

### Sessão exclusiva

- Campo `session_id` (UUID) adicionado ao model `Usuario`
- A cada login: novo UUID gerado, salvo no banco e embutido no JWT
- A cada requisição autenticada: middleware verifica se `session_id` do token bate com o do banco
- Novo login → novo `session_id` no banco → token anterior inválido → usuário anterior desconectado imediatamente

### Validade do token

- Access token: 15 minutos (renovado silenciosamente pelo app)
- Refresh token: 30 dias (renovado a cada uso — enquanto o policial usa o app regularmente, nunca expira)

---

## Feature 3 — Gestão de Usuários (Admin)

### Acesso

Tela visível apenas para usuários com `is_admin = true`. Ícone de acesso no header ou no menu lateral.

### Lista de usuários

Exibe: foto/avatar, nome, matrícula, posto/graduação, status (Ativo / Pausado)

### Criar usuário

1. Admin digita apenas a matrícula
2. Sistema gera senha aleatória
3. Modal exibe: *"Senha gerada: Xk9mPq2W — anote agora, não será exibida novamente"*
4. Usuário é criado sem nome/foto (preenche no próprio perfil após primeiro acesso)

### Ações por usuário

| Ação | Comportamento |
|---|---|
| Gerar nova senha | Gera nova senha única, exibe uma vez, invalida session_id atual (desconecta imediatamente) |
| Pausar | Apaga `session_id` no banco → desconectado imediatamente na próxima requisição |
| Reativar | Restaura acesso (usuário precisará de nova senha para entrar) |
| Excluir | Soft delete — dados preservados (LGPD) |

### Novos endpoints

- `GET /admin/usuarios` — lista todos os usuários da guarnição
- `POST /admin/usuarios` — cria usuário (matrícula), retorna senha gerada (plain text, única vez)
- `PATCH /admin/usuarios/{id}/pausar` — pausa acesso (limpa session_id)
- `PATCH /admin/usuarios/{id}/reativar` — reativa acesso
- `DELETE /admin/usuarios/{id}` — soft delete
- `POST /admin/usuarios/{id}/gerar-senha` — gera nova senha única, retorna plain text, limpa session_id

---

## Migrations necessárias

1. Adicionar `posto_graduacao VARCHAR(50)` à tabela `usuarios`
2. Adicionar `foto_url VARCHAR(500)` à tabela `usuarios`
3. Adicionar `session_id VARCHAR(36)` à tabela `usuarios`

---

## Impacto em código existente

- `app/models/usuario.py` — novos campos
- `app/schemas/auth.py` — atualizar `UsuarioRead`, novo schema `PerfilUpdate`
- `app/services/auth_service.py` — lógica de senha única + session_id no login
- `app/dependencies.py` — verificar session_id a cada requisição autenticada
- `app/api/v1/auth.py` — novos endpoints de perfil
- Nova router `app/api/v1/admin.py` — endpoints de gestão
- `frontend/index.html` — avatar no header, tela de perfil, tela de admin
