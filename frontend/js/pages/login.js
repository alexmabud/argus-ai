/**
 * Pagina de login — Argus AI.
 *
 * Tela de autenticacao com estetica cyberpunk tatica:
 * logo com glow ciano, scan line, campos animados,
 * indicador de status do servidor em tempo real.
 */
function renderLoginPage(appState) {
  return `
    <div class="login-container" x-data="loginForm()">
      <!-- Scan line animada -->
      <div class="login-scan-line"></div>

      <div class="login-card">
        <!-- Logo -->
        <div style="margin-bottom: 40px;">
          <div class="login-logo">ARGUS</div>
          <div class="login-subtitle">Sistema de Inteligencia Operacional</div>
        </div>

        <!-- Formulario -->
        <form @submit.prevent="submit()" style="display:flex;flex-direction:column;gap:20px;">
          <div class="login-field">
            <label class="login-field-label">ID Operacional</label>
            <input type="text"
                   x-model="matricula"
                   placeholder="Matricula"
                   required
                   autocomplete="username">
          </div>

          <div class="login-field">
            <label class="login-field-label">Senha</label>
            <input type="password"
                   x-model="senha"
                   placeholder="••••••••"
                   required
                   autocomplete="current-password">
          </div>

          <!-- Erro -->
          <div x-show="erro" x-cloak
               style="background: rgba(255,107,0,0.1); border: 1px solid rgba(255,107,0,0.3); border-radius: 4px; padding: 10px 14px;">
            <span style="color: var(--color-danger); font-size: 13px;" x-text="erro"></span>
          </div>

          <!-- Submit -->
          <button type="submit"
                  class="btn btn-primary"
                  :disabled="loading"
                  style="margin-top: 8px;">
            <span x-show="!loading">ACESSAR SISTEMA</span>
            <span x-show="loading" class="flex items-center gap-2">
              <span class="spinner"></span> AUTENTICANDO...
            </span>
          </button>
        </form>

        <!-- Status + versao -->
        <div style="margin-top: 32px; display:flex; flex-direction:column; align-items:center; gap:12px;">
          <div class="login-status">
            <span class="status-dot"
                  :class="navigator.onLine ? 'status-dot-online' : 'status-dot-offline'"></span>
            <span :style="navigator.onLine ? 'color: var(--color-success)' : 'color: var(--color-danger)'"
                  x-text="navigator.onLine ? 'SERVIDOR ONLINE' : 'SERVIDOR OFFLINE'"></span>
          </div>
          <div class="login-version">v1.0.0 // PMDF</div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Componente Alpine.js do formulario de login.
 *
 * Gerencia estado de matricula, senha, loading e erro.
 * Delega autenticacao para AuthManager e propaga login
 * para o componente app principal.
 */
function loginForm() {
  return {
    matricula: "",
    senha: "",
    loading: false,
    erro: null,

    /**
     * Submete formulario de login.
     *
     * Valida campos, chama auth.login() e propaga resultado
     * para o componente principal da aplicacao.
     */
    async submit() {
      if (!this.matricula || !this.senha) {
        this.erro = "Preencha matricula e senha.";
        return;
      }

      this.loading = true;
      this.erro = null;

      try {
        const user = await auth.login(this.matricula, this.senha);
        const appEl = document.querySelector("[x-data='app()']");
        if (appEl && appEl._x_dataStack) {
          appEl._x_dataStack[0].onLogin(user);
        }
      } catch (err) {
        this.erro = err.message || "Erro ao fazer login. Tente novamente.";
      } finally {
        this.loading = false;
      }
    },
  };
}
