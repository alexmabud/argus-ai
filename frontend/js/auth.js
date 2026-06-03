/**
 * Gerenciador de autenticação Argus AI.
 *
 * Controla login, logout, refresh e estado do usuário
 * autenticado via JWT armazenado em localStorage.
 */
class AuthManager {
  constructor() {
    this.user = null;
    this._loadUser();
  }

  _loadUser() {
    const stored = localStorage.getItem("argus_user");
    if (stored) {
      try {
        this.user = JSON.parse(stored);
      } catch {
        this.user = null;
      }
    }
  }

  isAuthenticated() {
    return !!api.token && !!this.user;
  }

  getUser() {
    return this.user;
  }

  async login(matricula, senha, totpCode = null) {
    const payload = { matricula, senha };
    if (totpCode) payload.totp_code = totpCode;
    const data = await api.post("/auth/login", payload);
    api.setTokens(data.access_token, data.refresh_token);

    // Buscar dados do usuário
    const user = await api.get("/auth/me");
    this.user = user;
    localStorage.setItem("argus_user", JSON.stringify(user));
    return user;
  }

  logout() {
    // Avisa o backend para limpar o cookie HTTPOnly. Faz best-effort —
    // mesmo se a chamada falhar, descartamos tokens locais.
    api.post("/auth/logout").catch(() => {});
    api.clearTokens();
    this.user = null;
    localStorage.removeItem("argus_user");
  }

  async fetchMe() {
    try {
      const user = await api.get("/auth/me");
      this.user = user;
      localStorage.setItem("argus_user", JSON.stringify(user));
      return user;
    } catch {
      this.logout();
      return null;
    }
  }
}

// Singleton global
const auth = new AuthManager();
