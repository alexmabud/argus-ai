/**
 * Aplicacao principal SPA — Argus AI.
 *
 * Router client-side com Alpine.js, gerenciamento de estado
 * global (autenticacao, navegacao, online/offline).
 * Tema: cyberpunk tatico / high-tech militar.
 */

// Registrar Service Worker (apos limpeza feita no head)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js?v=4").catch(() => {});
}

/**
 * Formata string de placa veicular inserindo traco automaticamente.
 * Aceita formato antigo (ABC-1234) e Mercosul (ABC1D23).
 * Remove caracteres invalidos e converte para maiusculas.
 *
 * @param {string} value - Valor bruto do input.
 * @returns {string} Placa formatada (ex: ABC-1234).
 */
function formatarPlaca(value) {
  const raw = value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 7);
  if (raw.length <= 3) return raw;
  return `${raw.slice(0, 3)}-${raw.slice(3)}`;
}

/**
 * Formata string de CPF inserindo pontos e traco automaticamente.
 * Remove caracteres nao numericos e aplica a mascara 000.000.000-00.
 *
 * @param {string} value - Valor bruto do input.
 * @returns {string} CPF formatado.
 */
function formatarCPF(value) {
  const d = value.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

/**
 * Formata string de data inserindo barras automaticamente (DD/MM/AAAA).
 * Remove caracteres nao numericos e aplica a mascara a medida que o usuario digita.
 *
 * @param {string} value - Valor bruto do input.
 * @returns {string} Data formatada (ex: 25/12/1990).
 */
function formatarData(value) {
  const d = value.replace(/\D/g, "").slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

/**
 * Converte data no formato DD/MM/AAAA para YYYY-MM-DD (formato ISO para API).
 * Retorna string vazia se o valor estiver incompleto ou invalido.
 *
 * @param {string} value - Data no formato DD/MM/AAAA.
 * @returns {string} Data no formato YYYY-MM-DD ou string vazia.
 */
function parseDateBR(value) {
  const parts = (value || "").split("/");
  if (parts.length !== 3 || parts[2].length !== 4) return "";
  return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
}

/**
 * Formata automaticamente como CPF se o valor contiver apenas digitos e separadores de CPF.
 * Usado nos campos de busca por nome/CPF para aplicar mascara em tempo real.
 *
 * @param {string} value - Valor digitado.
 * @returns {string} CPF formatado ou valor original sem alteracao.
 */
function formatarBuscaQuery(value) {
  if (/^[\d.\-]*$/.test(value) && value.replace(/\D/g, "").length > 0) {
    return formatarCPF(value);
  }
  return value;
}

// Mapa de abreviacoes de posto/graduacao PM
const POSTO_ABREV = {
  "Soldado": "SD",
  "Cabo": "CB",
  "3\u00ba Sargento": "3\u00ba SGT",
  "2\u00ba Sargento": "2\u00ba SGT",
  "1\u00ba Sargento": "1\u00ba SGT",
  "Subtenente": "ST",
  "Aspirante": "ASP",
  "2\u00ba Tenente": "2\u00ba TEN",
  "1\u00ba Tenente": "1\u00ba TEN",
  "Capit\u00e3o": "CAP",
  "Major": "MAJ",
  "Tenente-Coronel": "TC",
  "Coronel": "CEL",
};

/**
 * Componente Alpine.js principal da aplicacao.
 *
 * Gerencia estado global de autenticacao, navegacao entre paginas,
 * conectividade e sincronizacao offline. Atua como router SPA.
 */
function app() {
  return {
    // Estado global
    authenticated: false,
    currentPage: "home",
    user: null,
    online: navigator.onLine,
    syncPending: 0,

    /**
     * Inicializa a aplicacao: conectividade, auth, sync, IndexedDB.
     */
    async init() {
      // Monitorar conectividade
      window.addEventListener("online", () => { this.online = true; });
      window.addEventListener("offline", () => { this.online = false; });

      // Escutar expiracao de auth
      window.addEventListener("auth:expired", () => {
        this.authenticated = false;
        this.user = null;
        this.currentPage = "login";
      });

      // Escutar navegacao por evento customizado
      window.addEventListener("navigate", (e) => this.navigate(e.detail));

      // Escutar logout solicitado por componentes filhos
      window.addEventListener("auth:logout", () => this.logout());

      // Escutar atualizacao de dados do usuario (perfil/foto)
      window.addEventListener("user:updated", (e) => { this.user = e.detail; });

      // Verificar autenticacao existente
      if (auth.isAuthenticated()) {
        this.authenticated = true;
        this.user = auth.getUser();
        this.currentPage = "home";
        this.renderPage("home");
        document.body.style.overflow = "hidden";
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

    /**
     * Atualiza contagem de itens pendentes de sincronizacao.
     */
    async _updateSyncCount() {
      this.syncPending = await countPending();
    },

    /**
     * Navega para uma pagina da aplicacao.
     *
     * @param {string} page - Nome da pagina destino.
     */
    navigate(page) {
      this.currentPage = page;
      this.renderPage(page);
      window.history.pushState({ page }, "", `#${page}`);
      document.body.style.overflow = page === "home" ? "hidden" : "";
    },

    /**
     * Renderiza uma pagina no container principal.
     *
     * @param {string} page - Nome da pagina a renderizar.
     */
    renderPage(page) {
      const container = document.getElementById("page-content");
      if (!container) {
        const self = this;
        requestAnimationFrame(function() {
          const el = document.getElementById("page-content");
          if (el) {
            self._renderInto(el, page);
          }
        });
        return;
      }
      this._renderInto(container, page);
    },

    /**
     * Injeta HTML da pagina no container e inicializa Alpine nos novos elementos.
     */
    _renderInto(container, page) {
      const renderers = {
        home: renderHomePage,
        "abordagem-nova": renderAbordagemNova,
        consulta: renderConsulta,
        "pessoa-detalhe": renderPessoaDetalhe,
        "ocorrencia-upload": renderOcorrenciaUpload,
        dashboard: renderDashboard,
        perfil: renderPerfil,
        "admin-usuarios": renderAdminUsuarios,
      };

      // Destroi graficos ApexCharts antes de trocar de pagina para evitar
      // erros de NaN em SVGs orfaos que continuam tentando atualizar.
      container.querySelectorAll('[x-data]').forEach(el => {
        if (el._x_dataStack) {
          const data = el._x_dataStack[0];
          if (data._chartDia) { try { data._chartDia.destroy(); } catch {} }
          if (data._chartMes) { try { data._chartMes.destroy(); } catch {} }
        }
      });

      const render = renderers[page];
      if (render) {
        container.innerHTML = render(this);
        if (this.$nextTick) {
          this.$nextTick(() => {
            container.querySelectorAll("[x-data]").forEach((el) => {
              if (!el._x_dataStack) Alpine.initTree(el);
            });
          });
        }
      } else {
        container.innerHTML = `<p style="color: var(--color-text-muted);">Pagina nao encontrada.</p>`;
      }
    },

    /**
     * Renderiza a pagina de login no container dedicado.
     */
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

    /**
     * Callback apos login bem-sucedido.
     */
    async onLogin(user) {
      this.authenticated = true;
      this.user = user;
      this.navigate("home");
    },

    /**
     * Realiza logout e retorna para tela de login.
     */
    logout() {
      auth.logout();
      this.authenticated = false;
      this.user = null;
      this.currentPage = "login";
      this.$nextTick(() => this.renderLogin());
    },
  };
}

/**
 * Escapa caracteres especiais HTML para prevenir XSS.
 *
 * Deve ser aplicada em todo dado de usuario antes de interpolacao em innerHTML.
 *
 * @param {string} str - Valor a escapar.
 * @returns {string} Valor seguro para interpolacao em HTML.
 */
function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Renderiza a home page com saudacao e acoes rapidas.
 *
 * Cards no estilo glass + HUD tatico: fundo glassmorphism, clip-path no canto
 * inferior direito, scan line no hover, codigo tatico e glow no icone.
 * Animacao de entrada em stagger (60ms por card).
 */
function renderHomePage(appState) {
  const user = appState.user;
  const abrevRaw = user?.posto_graduacao ? (POSTO_ABREV[user.posto_graduacao] ?? user.posto_graduacao) : null;
  const guerraRaw = user?.nome_guerra || user?.nome || "Agente";
  const saudacao = abrevRaw ? `${escapeHtml(abrevRaw)} ${escapeHtml(guerraRaw)}` : escapeHtml(guerraRaw);

  const cards = [
    {
      code: '// ABD',
      page: 'abordagem-nova',
      label: 'Nova Abordagem',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>`,
    },
    {
      code: '// IA',
      page: 'consulta',
      label: 'Consulta IA',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
    },
    {
      code: '// OCR',
      page: 'ocorrencia-upload',
      label: 'Ocorr\u00eancia',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M12 12v6"/><path d="m15 15-3-3-3 3"/></svg>`,
    },
    {
      code: '// ANL',
      page: 'dashboard',
      label: 'Anal\u00edtico',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>`,
    },
  ];

  const cardsHtml = cards.map((c, i) => `
    <button onclick="document.querySelector('[x-data]')._x_dataStack[0].navigate('${c.page}')"
            class="home-action-card"
            style="animation-delay: ${i * 60}ms;">
      <div class="card-code">
        <span>${c.code}</span>
        <span>\u25c6</span>
      </div>
      <div class="card-icon">${c.icon}</div>
      <span class="card-label">${c.label}</span>
    </button>
  `).join('');

  return `
    <div class="home-layout">
      <div class="login-scan-line"></div>

      <div style="margin-bottom: 32px;">
        <h2 style="font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--color-text);">
          Ola, <span style="color: var(--color-primary);">${saudacao}</span>
        </h2>
        <p style="font-family: var(--font-data); font-size: 13px; color: var(--color-text-dim); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.08em;">
          Memoria Operacional // Status Ativo
        </p>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
        ${cardsHtml}
      </div>
    </div>
  `;
}

/**
 * Exibe toast notification temporario.
 *
 * @param {string} message - Texto da notificacao.
 * @param {string} type - Tipo: success, error, warning.
 * @param {number} duration - Duracao em ms (padrao 3000).
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
