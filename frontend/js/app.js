/**
 * Aplicação principal SPA — Argus AI.
 *
 * Router client-side com Alpine.js, gerenciamento de estado
 * global (autenticação, navegação, online/offline).
 * Tema: cyberpunk tático / high-tech militar.
 */

// Registrar Service Worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// Ignorar erros de extensões do Chrome (chrome.runtime.sendMessage)
// que tentam se comunicar com isolated worlds.
// Esses erros não afetam funcionalidade — vêm de extensões externas.
window.addEventListener("unhandledrejection", (event) => {
  const msg = event.reason?.message || String(event.reason);
  if (msg.includes("Could not establish connection") ||
      msg.includes("Receiving end does not exist") ||
      msg.includes("Extension context invalidated")) {
    event.preventDefault();
  }
});

// Também suprimir via error event (some extensions may trigger this way)
window.addEventListener("error", (event) => {
  const msg = (event.message || "").toLowerCase();
  if (msg.includes("could not establish connection") ||
      msg.includes("receiving end does not exist")) {
    return true; // Retorna true para suprimir
  }
}, true); // Usa capture phase

/**
 * Formata string de placa veicular inserindo traço automaticamente.
 * Aceita formato antigo (ABC-1234) e Mercosul (ABC1D23).
 * Remove caracteres inválidos e converte para maiúsculas.
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
 * Formata string de CPF inserindo pontos e traço automaticamente.
 * Remove caracteres não numéricos e aplica a máscara 000.000.000-00.
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
 * Valida CPF pelo algoritmo de dois dígitos verificadores.
 * Rejeita CPFs com todos os dígitos iguais (ex: 111.111.111-11).
 *
 * @param {string} value - CPF com ou sem máscara.
 * @returns {boolean} true se o CPF for válido.
 */
function validarCPF(value) {
  const d = value.replace(/\D/g, "");
  if (d.length !== 11) return false;
  if (/^(\d)\1+$/.test(d)) return false;

  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(d[i]) * (10 - i);
  let resto = soma % 11;
  const dig1 = resto < 2 ? 0 : 11 - resto;
  if (parseInt(d[9]) !== dig1) return false;

  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(d[i]) * (11 - i);
  resto = soma % 11;
  const dig2 = resto < 2 ? 0 : 11 - resto;
  return parseInt(d[10]) === dig2;
}

/**
 * Formata string de data inserindo barras automaticamente (DD/MM/AAAA).
 * Remove caracteres não numéricos e aplica a máscara à medida que o usuário digita.
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
 * Retorna string vazia se o valor estiver incompleto ou inválido.
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
 * Formata automaticamente como CPF se o valor contiver apenas dígitos e separadores de CPF.
 * Usado nos campos de busca por nome/CPF para aplicar máscara em tempo real.
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

// Mapa de abreviações de posto/graduação PM
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
 * Componente Alpine.js principal da aplicação.
 *
 * Gerencia estado global de autenticação, navegação entre páginas,
 * conectividade e sincronização offline. Atua como router SPA.
 */
function app() {
  return {
    // Estado global
    authenticated: false,
    currentPage: "home",
    user: null,
    online: navigator.onLine,
    syncPending: 0,
    navHistory: [],
    _popstateHandler: null,

    /**
     * Inicializa a aplicação: conectividade, auth, sync, IndexedDB.
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
        this.$nextTick(() => this.renderLogin());
      });

      // Escutar navegacao por evento customizado
      window.addEventListener("navigate", (e) => this.navigate(e.detail));

      // Escutar logout solicitado por componentes filhos
      window.addEventListener("auth:logout", () => this.logout());

      // Capturar back físico do celular / browser (evitar registro duplicado).
      // Nota: popstate dispara tanto para back quanto forward — forward navigation
      // não é diferenciado intencionalmente (PWA não expõe botão avançar).
      if (!this._popstateHandler) {
        this._popstateHandler = () => this.goBack();
        window.addEventListener("popstate", this._popstateHandler);
      }

      // Escutar atualizacao de dados do usuario (perfil/foto)
      window.addEventListener("user:updated", (e) => { this.user = e.detail; });

      // Verificar autenticacao existente
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
        this.$nextTick(() => this.renderLogin());
      }

      // Iniciar IndexedDB
      try {
        await initDB();
      } catch (err) {
        console.warn("[Argus] IndexedDB indisponível:", err.message);
      }

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
     * Atualiza contagem de itens pendentes de sincronização.
     */
    async _updateSyncCount() {
      this.syncPending = await countPending();
    },

    /**
     * Navega para uma página da aplicação.
     *
     * Empurra a página atual no stack de histórico interno antes de trocar,
     * permitindo que goBack() retorne a página anterior corretamente.
     *
     * Args:
     *     page: Nome da página destino.
     */
    navigate(page) {
      if (this.currentPage && this.currentPage !== page) {
        this.navHistory.push(this.currentPage);
      }
      this.currentPage = page;
      this.renderPage(page);
      window.history.pushState({ page }, "", `#${page}`);
      document.body.style.overflow = page === "home" ? "hidden" : "";
      window.scrollTo(0, 0);
    },

    /**
     * Navega para a página anterior no histórico interno.
     *
     * Faz pop do stack navHistory e renderiza a página anterior.
     * Usa replaceState para não empilhar mais uma entrada no histórico do browser.
     * Fallback para 'home' se o histórico estiver vazio.
     */
    goBack() {
      const prev = this.navHistory.pop() || "home";
      this.currentPage = prev;
      this.renderPage(prev);
      window.history.replaceState({ page: prev }, "", `#${prev}`);
      document.body.style.overflow = prev === "home" ? "hidden" : "";
      window.scrollTo(0, 0);
    },

    /**
     * Renderiza uma pagina no container principal.
     *
     * @param {string} page - Nome da página a renderizar.
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
     * Injeta HTML da página no container e inicializa Alpine nos novos elementos.
     */
    _renderInto(container, page) {
      const renderers = {
        home: renderHomePage,
        "abordagem-nova": renderAbordagemNova,
        consulta: renderConsulta,
        "pessoa-detalhe": renderPessoaDetalhe,
        "ocorrencias": renderOcorrencias,
        "abordagem-detalhe": renderAbordagemDetalhe,
        dashboard: renderDashboard,
        perfil: renderPerfil,
        "admin-usuarios": renderAdminUsuarios,
      };

      // Destrói gráficos ApexCharts antes de trocar de página para evitar
      // erros de NaN em SVGs órfãos que continuam tentando atualizar.
      container.querySelectorAll('[x-data]').forEach(el => {
        if (el._x_dataStack) {
          const data = el._x_dataStack[0];
          if (data._chartDia) { try { data._chartDia.destroy(); } catch {} }
          if (data._chartMes) { try { data._chartMes.destroy(); } catch {} }
          if (data.destroyMapaAnalitico) { try { data.destroyMapaAnalitico(); } catch {} }
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
        container.innerHTML = `<p style="color: var(--color-text-muted);">Página não encontrada.</p>`;
      }
    },

    /**
     * Renderiza a página de login no container dedicado.
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
     * Callback após login bem-sucedido.
     */
    async onLogin(user) {
      this.authenticated = true;
      this.user = user;
      this.navigate("home");
      if (this._perfilIncompleto(user)) {
        this.$nextTick(() => this._mostrarModalCompletarPerfil());
      }
    },

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
      return !user.nome?.trim() || !user.posto_graduacao?.trim() || !user.nome_guerra?.trim();
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

      // Guard: POSTOS_GRADUACAO é definido em perfil.js (carregado antes de app.js).
      const postos = typeof POSTOS_GRADUACAO !== "undefined" ? POSTOS_GRADUACAO : [];
      const postoOpts = postos.map(
        (p) => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`
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
 * Componente Alpine.js do formulário de completar perfil.
 *
 * Usado pelo modal bloqueante exibido quando usuário comum
 * abre o sistema com perfil incompleto. Salva via PUT /auth/perfil.
 */
function completarPerfilModal() {
  const user = auth.getUser() || {};
  return {
    nome: (user.nome && user.nome !== user.matricula) ? user.nome : "",
    nomeGuerra: user.nome_guerra || "",
    posto: user.posto_graduacao || "",
    salvando: false,

    async salvar() {
      if (!this.nome.trim() || !this.nomeGuerra.trim() || !this.posto) {
        showToast("Preencha todos os campos", "error");
        return;
      }
      if (this.nome.trim().length < 2) {
        showToast("Nome deve ter ao menos 2 caracteres", "error");
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
      } catch (e) {
        console.error("[Argus] completarPerfilModal.salvar:", e);
        showToast("Erro ao salvar perfil", "error");
      } finally {
        this.salvando = false;
      }
    },
  };
}

/**
 * Escapa caracteres especiais HTML para prevenir XSS.
 *
 * Deve ser aplicada em todo dado de usuário antes de interpolação em innerHTML.
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
 * Renderiza a home page com saudação e ações rápidas.
 *
 * Cards no estilo glass + HUD tático: fundo glassmorphism, clip-path no canto
 * inferior direito, scan line no hover, código tático e glow no ícone.
 * Animação de entrada em stagger (60ms por card).
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
      page: 'ocorrencias',
      label: 'Relat\u00f3rios',
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
          Olá, <span style="color: var(--color-primary);">${saudacao}</span>
        </h2>
        <p style="font-family: var(--font-data); font-size: 13px; color: var(--color-text-dim); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.08em;">
          Memória Operacional // Status Ativo
        </p>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
        ${cardsHtml}
      </div>
    </div>
  `;
}

/**
 * Exibe toast notification temporário.
 *
 * @param {string} message - Texto da notificação.
 * @param {string} type - Tipo: success, error, warning.
 * @param {number} duration - Duração em ms (padrão 3000).
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
