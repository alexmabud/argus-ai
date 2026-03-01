/**
 * Página de login — Argus AI.
 *
 * Formulário de autenticação com matrícula e senha,
 * loading state e exibição de erro.
 */
function renderLoginPage(appState) {
  return `
    <div class="min-h-screen flex items-center justify-center px-6"
         x-data="loginForm()">
      <div class="w-full max-w-sm space-y-8">
        <!-- Logo -->
        <div class="text-center">
          <h1 class="text-3xl font-bold text-blue-400">Argus AI</h1>
          <p class="text-slate-400 text-sm mt-2">Sistema de apoio operacional</p>
        </div>

        <!-- Formulário -->
        <form @submit.prevent="submit()" class="space-y-4">
          <div>
            <label class="block text-sm text-slate-300 mb-1">Matrícula</label>
            <input type="text"
                   x-model="matricula"
                   placeholder="Digite sua matrícula"
                   required
                   autocomplete="username"
                   class="w-full">
          </div>

          <div>
            <label class="block text-sm text-slate-300 mb-1">Senha</label>
            <input type="password"
                   x-model="senha"
                   placeholder="Digite sua senha"
                   required
                   autocomplete="current-password"
                   class="w-full">
          </div>

          <!-- Erro -->
          <div x-show="erro" x-cloak
               class="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3">
            <span x-text="erro"></span>
          </div>

          <!-- Submit -->
          <button type="submit"
                  class="btn btn-primary"
                  :disabled="loading">
            <span x-show="!loading">Entrar</span>
            <span x-show="loading" class="flex items-center gap-2">
              <span class="spinner"></span> Entrando...
            </span>
          </button>
        </form>

        <p class="text-center text-slate-500 text-xs">
          v2.0 — Memória operacional da guarnição
        </p>
      </div>
    </div>
  `;
}

function loginForm() {
  return {
    matricula: "",
    senha: "",
    loading: false,
    erro: null,

    async submit() {
      if (!this.matricula || !this.senha) {
        this.erro = "Preencha matrícula e senha.";
        return;
      }

      this.loading = true;
      this.erro = null;

      try {
        const user = await auth.login(this.matricula, this.senha);
        // Propagar para o app principal
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
