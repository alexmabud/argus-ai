# Modal Bloqueante de Perfil Incompleto — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir um modal fullscreen bloqueante quando o usuário comum abre o sistema com `nome`, `posto_graduacao` ou `nome_guerra` vazios — liberando o acesso somente após o preenchimento.

**Architecture:** Verificação puramente no frontend usando os dados já presentes em `auth.getUser()` (localStorage). Sem chamadas extras de rede. Modal criado dinamicamente via JS com Alpine.js, mesmo padrão do `mostrarModalSaida()`. Dois pontos de disparo: `onLogin()` e `init()` em `app.js`.

**Tech Stack:** Alpine.js (já carregado globalmente), endpoint existente `PUT /auth/perfil`

**Design doc:** `docs/plans/2026-04-19-modal-perfil-incompleto-design.md`

---

## Task 1: Adicionar `completarPerfilModal()` em `app.js`

**Files:**
- Modify: `frontend/js/app.js` (inserir após linha 370, antes de `escapeHtml`)

**Step 1: Localizar ponto de inserção**

Abrir `frontend/js/app.js`. Encontrar a linha:

```js
/**
 * Escapa caracteres especiais HTML para prevenir XSS.
```

Esse comentário fica logo após o fechamento da função `app()` (linha ~372). Inserir o novo código **antes** desse comentário.

**Step 2: Inserir a função `completarPerfilModal()`**

Inserir entre o `}` que fecha `app()` e o comentário de `escapeHtml`:

```js
/**
 * Componente Alpine.js do formulário de completar perfil.
 *
 * Usado pelo modal bloqueante exibido quando usuário comum
 * abre o sistema com perfil incompleto. Salva via PUT /auth/perfil.
 */
function completarPerfilModal() {
  const user = auth.getUser() || {};
  return {
    nome: user.nome || "",
    nomeGuerra: user.nome_guerra || "",
    posto: user.posto_graduacao || "",
    salvando: false,

    async salvar() {
      if (!this.nome.trim() || !this.nomeGuerra.trim() || !this.posto) {
        showToast("Preencha todos os campos", "error");
        return;
      }
      this.salvando = true;
      try {
        const updated = await api.put("/auth/perfil", {
          nome: this.nome.trim(),
          nome_guerra: this.nomeGuerra.trim(),
          posto_graduacao: this.posto,
        });
        auth.user = updated;
        localStorage.setItem("argus_user", JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent("user:updated", { detail: updated }));
        document.getElementById("modal-completar-perfil")?.remove();
        showToast("Perfil atualizado com sucesso", "success");
      } catch {
        showToast("Erro ao salvar perfil", "error");
      } finally {
        this.salvando = false;
      }
    },
  };
}
```

**Step 3: Commit parcial**

```bash
git add frontend/js/app.js
git commit -m "feat(frontend): adicionar completarPerfilModal() para modal de perfil incompleto"
```

---

## Task 2: Adicionar métodos `_perfilIncompleto` e `_mostrarModalCompletarPerfil` ao objeto `app()`

**Files:**
- Modify: `frontend/js/app.js` (dentro do objeto retornado por `app()`, antes de `logout`)

**Step 1: Localizar ponto de inserção**

Dentro do objeto `app()`, encontrar o método `logout()`:

```js
    /**
     * Realiza logout e retorna para tela de login.
     */
    logout() {
```

Inserir os dois novos métodos **antes** de `logout()`.

**Step 2: Inserir `_perfilIncompleto` e `_mostrarModalCompletarPerfil`**

```js
    /**
     * Verifica se o perfil do usuário está incompleto.
     *
     * Retorna false para admins — eles não precisam completar perfil.
     * Campos obrigatórios: nome, posto_graduacao, nome_guerra.
     *
     * @param {object} user - Objeto do usuário autenticado.
     * @returns {boolean} true se perfil incompleto e usuário não é admin.
     */
    _perfilIncompleto(user) {
      if (!user || user.is_admin) return false;
      return !user.nome?.trim() || !user.posto_graduacao || !user.nome_guerra?.trim();
    },

    /**
     * Exibe modal fullscreen bloqueante para completar perfil.
     *
     * Cria overlay dinamicamente e inicializa Alpine no elemento.
     * Guard contra dupla exibição via id único no DOM.
     * Fecha automaticamente após salvar com sucesso (via completarPerfilModal).
     */
    _mostrarModalCompletarPerfil() {
      if (document.getElementById("modal-completar-perfil")) return;

      const postoOpts = POSTOS_GRADUACAO.map(
        (p) => `<option value="${p}">${p}</option>`
      ).join("");

      const overlay = document.createElement("div");
      overlay.id = "modal-completar-perfil";
      overlay.style.cssText =
        "position:fixed;inset:0;background:rgba(5,10,15,0.92);display:flex;align-items:center;justify-content:center;z-index:9999;padding:16px;";

      overlay.innerHTML = `
        <div class="glass-card" style="padding:24px;max-width:400px;width:100%;border:1px solid var(--color-primary);" x-data="completarPerfilModal()">
          <div style="margin-bottom:20px;">
            <h3 style="color:var(--color-primary);font-family:var(--font-display);font-weight:700;font-size:16px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
              Complete seu perfil
            </h3>
            <p style="color:var(--color-text-muted);font-family:var(--font-body);font-size:13px;">
              Para usar o sistema, preencha seus dados de identificação.
            </p>
          </div>
          <div style="display:flex;flex-direction:column;gap:14px;">
            <div>
              <label class="login-field-label">Nome completo</label>
              <input type="text" x-model="nome" placeholder="Seu nome completo" maxlength="200" />
            </div>
            <div>
              <label class="login-field-label">Nome de guerra</label>
              <input type="text" x-model="nomeGuerra" placeholder="Ex: Silva" maxlength="50" />
            </div>
            <div>
              <label class="login-field-label">Posto / Graduação</label>
              <select x-model="posto">
                <option value="">Selecione...</option>
                ${postoOpts}
              </select>
            </div>
            <button @click="salvar()" :disabled="salvando" class="btn btn-primary" style="width:100%;margin-top:4px;">
              <span x-show="!salvando">Salvar e continuar</span>
              <span x-show="salvando">Salvando...</span>
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
      Alpine.initTree(overlay);
    },

```

**Step 3: Commit parcial**

```bash
git add frontend/js/app.js
git commit -m "feat(frontend): adicionar _perfilIncompleto e _mostrarModalCompletarPerfil ao app()"
```

---

## Task 3: Disparar verificação em `onLogin()` e `init()`

**Files:**
- Modify: `frontend/js/app.js` — dois pontos dentro do objeto `app()`

**Step 1: Modificar `onLogin(user)`**

Encontrar:

```js
    async onLogin(user) {
      this.authenticated = true;
      this.user = user;
      this.navigate("home");
    },
```

Substituir por:

```js
    async onLogin(user) {
      this.authenticated = true;
      this.user = user;
      this.navigate("home");
      if (this._perfilIncompleto(user)) {
        this.$nextTick(() => this._mostrarModalCompletarPerfil());
      }
    },
```

**Step 2: Modificar `init()` — bloco de sessão existente**

Encontrar:

```js
      if (auth.isAuthenticated()) {
        this.authenticated = true;
        this.user = auth.getUser();
        this.currentPage = "home";
        this.renderPage("home");
        document.body.style.overflow = "hidden";
      } else {
```

Substituir por:

```js
      if (auth.isAuthenticated()) {
        this.authenticated = true;
        this.user = auth.getUser();
        this.currentPage = "home";
        this.renderPage("home");
        document.body.style.overflow = "hidden";
        if (this._perfilIncompleto(this.user)) {
          this.$nextTick(() => this._mostrarModalCompletarPerfil());
        }
      } else {
```

**Step 3: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat(frontend): exibir modal bloqueante quando perfil do usuário está incompleto"
```

---

## Task 4: Teste manual

Não há framework de testes frontend no projeto. Executar os cenários abaixo manualmente com o servidor rodando (`make dev`).

**Setup:** Ter um usuário comum com `posto_graduacao` e `nome_guerra` nulos (recém-criado pelo admin, ou limpar via admin do DB).

**Cenário 1 — Login com perfil incompleto**
1. Fazer login com usuário comum sem posto/nome de guerra
2. Esperado: após login, modal "Complete seu perfil" aparece sobre a home
3. Tentar navegar (botão back do browser) — esperado: modal permanece
4. Preencher apenas nome e nome de guerra, não selecionar posto → clicar Salvar
5. Esperado: toast "Preencha todos os campos", modal não fecha
6. Preencher os 3 campos → clicar Salvar
7. Esperado: modal fecha, toast "Perfil atualizado com sucesso", home liberada

**Cenário 2 — App aberto com sessão existente e perfil incompleto**
1. Com usuário autenticado (token no localStorage) e perfil incompleto
2. Recarregar a página (F5)
3. Esperado: modal aparece imediatamente sem precisar fazer login

**Cenário 3 — Perfil completo (caminho normal)**
1. Login com usuário que tem nome + posto + nome de guerra preenchidos
2. Esperado: nenhum modal — home abre normalmente

**Cenário 4 — Admin**
1. Login com usuário `is_admin: true` que não tem posto/nome de guerra
2. Esperado: nenhum modal — admin vai direto para home

**Cenário 5 — Dupla exibição (guard)**
1. No console do browser, chamar `document.querySelector('[x-data]')._x_dataStack[0]._mostrarModalCompletarPerfil()` duas vezes
2. Esperado: apenas um modal no DOM (guard `if getElementById` previne duplicata)

---

## Task 5: Commit final e tag

```bash
git add frontend/js/app.js
git commit -m "feat(frontend): modal bloqueante de perfil incompleto para usuários comuns"
```
