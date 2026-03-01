/**
 * Aplicação principal SPA — Argus AI.
 *
 * Router client-side com Alpine.js, gerenciamento de estado
 * global (autenticação, navegação, online/offline).
 */

// Registrar Service Worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

/**
 * Componente Alpine.js principal da aplicação.
 */
function app() {
  return {
    // Estado global
    authenticated: false,
    currentPage: "home",
    user: null,
    online: navigator.onLine,
    syncPending: 0,

    async init() {
      // Monitorar conectividade
      window.addEventListener("online", () => { this.online = true; });
      window.addEventListener("offline", () => { this.online = false; });

      // Escutar expiração de auth
      window.addEventListener("auth:expired", () => {
        this.authenticated = false;
        this.user = null;
        this.currentPage = "login";
      });

      // Verificar autenticação existente
      if (auth.isAuthenticated()) {
        this.authenticated = true;
        this.user = auth.getUser();
        this.navigate("home");
      } else {
        this.$nextTick(() => this.renderLogin());
      }

      // Iniciar IndexedDB
      await initDB();

      // Iniciar sync manager
      syncManager.onStatusChange = (status, detail) => {
        if (status === "done") {
          this._updateSyncCount();
          if (detail.synced > 0) {
            showToast(`${detail.synced} item(ns) sincronizado(s)`, "success");
          }
          if (detail.failed > 0) {
            showToast(`${detail.failed} item(ns) com erro`, "error");
          }
        }
      };
      syncManager.start();
      this._updateSyncCount();
    },

    async _updateSyncCount() {
      this.syncPending = await countPending();
    },

    navigate(page) {
      this.currentPage = page;
      this.renderPage(page);
      window.history.pushState({ page }, "", `#${page}`);
    },

    renderPage(page) {
      const container = document.getElementById("page-content");
      if (!container) return;

      const renderers = {
        home: renderHomePage,
        "abordagem-nova": renderAbordagemNova,
        consulta: renderConsulta,
        "pessoa-detalhe": renderPessoaDetalhe,
        "ocorrencia-upload": renderOcorrenciaUpload,
        "rag-relatorio": renderRagRelatorio,
        dashboard: renderDashboard,
      };

      const render = renderers[page];
      if (render) {
        container.innerHTML = render(this);
        // Re-init Alpine para novos elementos
        this.$nextTick(() => {
          container.querySelectorAll("[x-data]").forEach((el) => {
            if (!el._x_dataStack) Alpine.initTree(el);
          });
        });
      } else {
        container.innerHTML = `<p class="text-slate-400">Página não encontrada.</p>`;
      }
    },

    renderLogin() {
      const loginContainer = document.getElementById("page-login");
      if (loginContainer) {
        loginContainer.innerHTML = renderLoginPage(this);
        this.$nextTick(() => {
          loginContainer.querySelectorAll("[x-data]").forEach((el) => {
            if (!el._x_dataStack) Alpine.initTree(el);
          });
        });
      }
    },

    async onLogin(user) {
      this.authenticated = true;
      this.user = user;
      this.navigate("home");
    },

    logout() {
      auth.logout();
      this.authenticated = false;
      this.user = null;
      this.currentPage = "login";
      this.$nextTick(() => this.renderLogin());
    },
  };
}

// Home page simples
function renderHomePage(appState) {
  const user = appState.user;
  const nome = user?.nome || "Agente";
  return `
    <div class="space-y-6">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Olá, ${nome}</h2>
        <p class="text-slate-400 text-sm mt-1">Argus AI — Memória operacional da guarnição</p>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('abordagem-nova')"
                class="card text-center py-6 hover:border-blue-500 transition-colors cursor-pointer">
          <svg class="mx-auto mb-2 w-8 h-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>
          <span class="text-sm font-medium">Nova Abordagem</span>
        </button>

        <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('consulta')"
                class="card text-center py-6 hover:border-blue-500 transition-colors cursor-pointer">
          <svg class="mx-auto mb-2 w-8 h-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>
          <span class="text-sm font-medium">Consulta</span>
        </button>

        <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('ocorrencia-upload')"
                class="card text-center py-6 hover:border-blue-500 transition-colors cursor-pointer">
          <svg class="mx-auto mb-2 w-8 h-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>
          <span class="text-sm font-medium">Ocorrência</span>
        </button>

        <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('rag-relatorio')"
                class="card text-center py-6 hover:border-blue-500 transition-colors cursor-pointer">
          <svg class="mx-auto mb-2 w-8 h-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"/></svg>
          <span class="text-sm font-medium">Relatório IA</span>
        </button>
      </div>

      <div class="card">
        <h3 class="text-sm font-semibold text-slate-300 mb-2">Acesso rápido</h3>
        <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('dashboard')"
                class="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-700 text-sm text-slate-300 transition-colors">
          Dashboard analítico
        </button>
      </div>
    </div>
  `;
}

/**
 * Exibe toast notification temporário.
 */
function showToast(message, type = "success", duration = 3000) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}
