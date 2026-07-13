/**
 * Gerenciador de autenticação Argus AI.
 *
 * Controla login, logout, refresh e estado do usuário.
 * Autenticação via cookie HttpOnly (argus_access_token).
 * argus_user (perfil não-credencial) persiste em localStorage para UX offline.
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
    // Cookie HttpOnly garante a autenticação real; argus_user (localStorage)
    // é só o indicador local de sessão ativa (não guarda credencial).
    return !!this.user;
  }

  getUser() {
    return this.user;
  }

  async login(matricula, senha, totpCode = null) {
    const payload = { matricula, senha };
    if (totpCode) payload.totp_code = totpCode;
    // Tokens chegam via cookie HttpOnly (Set-Cookie) — o corpo não traz mais
    // access_token/refresh_token (achado #13/2026-07-13).
    await api.post("/auth/login", payload);

    // Buscar dados do usuário
    const user = await api.get("/auth/me");
    this.user = user;
    localStorage.setItem("argus_user", JSON.stringify(user));
    // Ativa a criptografia do IndexedDB antes de qualquer cache de PII.
    if (typeof ensureCryptoReady === "function") {
      await ensureCryptoReady().catch(() => {});
    }
    return user;
  }

  logout() {
    // Avisa o backend para limpar o cookie HTTPOnly. Faz best-effort —
    // mesmo se a chamada falhar, descartamos tokens locais.
    api.post("/auth/logout").catch(() => {});
    api.clearTokens();
    this.user = null;
    localStorage.removeItem("argus_user");
    // Limpa dados sensíveis locais (PII no IndexedDB + respostas de API
    // cacheadas no Service Worker) — evita vazamento em dispositivo compartilhado.
    if (typeof clearLocalDB === "function") clearLocalDB().catch(() => {});
    if (self.caches) {
      caches
        .keys()
        .then((keys) =>
          Promise.all(keys.filter((k) => k.startsWith("argus-")).map((k) => caches.delete(k))),
        )
        .catch(() => {});
    }
  }

  async fetchMe() {
    try {
      const user = await api.get("/auth/me");
      this.user = user;
      localStorage.setItem("argus_user", JSON.stringify(user));
      return user;
    } catch (err) {
      // Só desloga em falha de AUTENTICAÇÃO (401). Erro de rede/offline (status
      // 0) ou erro do servidor (5xx) NÃO pode deslogar nem apagar a fila offline
      // — deslogar no boot offline causaria perda de dados de campo não
      // sincronizados. Mantém a sessão existente (cookie HttpOnly + argus_user).
      if (err && err.status === 401) {
        this.logout();
        return null;
      }
      return this.user;
    }
  }
}

// Singleton global
const auth = new AuthManager();
