/**
 * Cliente HTTP para API Argus AI.
 *
 * Gerencia requisições com retry exponencial, refresh automático
 * de token JWT e tratamento de rate limiting.
 */
class ApiClient {
  constructor() {
    this.baseUrl = "/api/v1";
    // Tokens não ficam em localStorage — autenticação via cookie HttpOnly.
    // argus_user (perfil não-credencial) permanece em localStorage para UX offline.
    this.token = null;
    this._refreshPromise = null;
  }

  setTokens(access, _refresh) {
    // Mantém token em memória para requests síncronos do ciclo de vida atual.
    // Cookie argus_access_token (HttpOnly) é a fonte canônica — não persiste em localStorage.
    this.token = access;
  }

  clearTokens() {
    this.token = null;
    localStorage.removeItem("argus_user");
    // Limpar vestígios de versões anteriores que salvavam tokens em localStorage
    localStorage.removeItem("argus_token");
    localStorage.removeItem("argus_refresh_token");
  }

  async request(method, path, body = null, retries = 2) {
    const url = `${this.baseUrl}${path}`;
    const headers = {};

    // Cookie HttpOnly (argus_access_token) é enviado automaticamente via
    // credentials: "same-origin" — sem header Authorization explícito.
    const options = { method, headers, credentials: "same-origin" };

    if (body && !(body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
      options.body = body;
    }

    try {
      const response = await fetch(url, options);

      // Token expirado — tentar refresh silencioso via cookie.
      // Endpoints de auth não usam refresh: o 401 deles é rejeição de credencial,
      // não expiração de sessão. Tentar refresh causaria loop e dispararia auth:expired
      // no meio do fluxo de login, impedindo o campo 2FA de aparecer.
      if (response.status === 401) {
        const isAuthEndpoint = path === "/auth/login" || path === "/auth/refresh";
        if (isAuthEndpoint) {
          const errData = await response.json().catch(() => ({}));
          const msg = typeof errData.detail === "string" ? errData.detail : "Credenciais inválidas";
          throw new ApiError(401, msg);
        }
        const refreshResult = await this._refreshAccessToken();
        if (refreshResult === "ok") {
          const retryResponse = await fetch(url, options);
          if (retryResponse.ok) return await retryResponse.json();
          const retryErr = await retryResponse.json().catch(() => ({}));
          const retryDetail = retryErr.detail;
          const retryMsg = typeof retryDetail === "string" ? retryDetail : "Erro na requisição";
          throw new ApiError(retryResponse.status, retryMsg);
        }
        if (refreshResult === "invalid") {
          // Sessão realmente inválida (servidor confirmou) — logout
          this.clearTokens();
          window.dispatchEvent(new Event("auth:expired"));
          throw new ApiError(401, "Sessão expirada");
        }
        // refreshResult === "network_error" — rede instável, não destruir sessão
        throw new ApiError(0, "Sem conexão com o servidor");
      }

      // Rate limit
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get("Retry-After") || "2");
        if (retries > 0) {
          await this._sleep(retryAfter * 1000);
          return this.request(method, path, body, retries - 1);
        }
        throw new ApiError(429, "Muitas requisições. Tente novamente.");
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail;
        const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((d) => d.msg || d).join("; ") : "Erro na requisição";
        throw new ApiError(response.status, msg);
      }

      if (response.status === 204) return null;
      return await response.json();
    } catch (err) {
      if (err instanceof ApiError) throw err;

      // Network error — retry com backoff
      if (retries > 0) {
        await this._sleep(1000 * (3 - retries));
        return this.request(method, path, body, retries - 1);
      }
      throw new ApiError(0, "Sem conexão com o servidor");
    }
  }

  /**
   * Renova o access token via refresh token com retry resiliente.
   *
   * @returns {Promise<"ok"|"invalid"|"network_error">}
   *   - "ok": refresh bem-sucedido, novos tokens salvos
   *   - "invalid": servidor confirmou sessão inválida (401) — logout necessário
   *   - "network_error": falha de rede após 3 tentativas — tokens preservados
   */
  async _refreshAccessToken() {
    // Mutex: se já existe um refresh em andamento, aguarda o resultado dele
    // em vez de disparar outro (evita race condition com requests paralelas)
    if (this._refreshPromise) return this._refreshPromise;

    this._refreshPromise = (async () => {
      const maxRetries = 3;
      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          // Corpo vazio — o backend lê o refresh token do cookie HttpOnly.
          const response = await fetch(`${this.baseUrl}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
            credentials: "same-origin",
          });
          if (response.ok) {
            const data = await response.json();
            this.setTokens(data.access_token, null);
            return "ok";
          }
          // 401 = sessão realmente inválida no servidor, não adianta tentar de novo
          if (response.status === 401) return "invalid";
          // Outros erros do servidor (500, 502, 503) — tentar de novo
        } catch {
          // Erro de rede — tentar de novo
        }
        if (attempt < maxRetries - 1) {
          await this._sleep(1000 * (attempt + 1));
        }
      }
      // Esgotou tentativas sem resposta do servidor — preservar sessão
      return "network_error";
    })();

    try {
      return await this._refreshPromise;
    } finally {
      this._refreshPromise = null;
    }
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  get(path) { return this.request("GET", path); }
  post(path, body) { return this.request("POST", path, body); }
  postForm(path, formData) { return this.request("POST", path, formData); }
  put(path, body) { return this.request("PUT", path, body); }
  del(path) { return this.request("DELETE", path); }
  patch(path, body) { return this.request("PATCH", path, body); }
  delete(path) { return this.request("DELETE", path); }
  uploadForm(path, formData) { return this.request("POST", path, formData); }

  async downloadBlob(path) {
    const url = `${this.baseUrl}${path}`;
    const headers = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    let response = await fetch(url, { method: "GET", headers });
    if (response.status === 401 && this.refreshToken) {
      const refreshResult = await this._refreshAccessToken();
      if (refreshResult === "ok") {
        headers["Authorization"] = `Bearer ${this.token}`;
        response = await fetch(url, { method: "GET", headers });
      } else if (refreshResult === "invalid") {
        this.clearTokens();
        window.dispatchEvent(new Event("auth:expired"));
        throw new ApiError(401, "Sessão expirada");
      }
    }
    if (!response.ok) throw new ApiError(response.status, "Erro no download");
    return response;
  }

  async uploadFile(path, file, extraData = {}, fieldName = "file") {
    const compressed = typeof compressImage === "function"
      ? await compressImage(file)
      : file;
    const form = new FormData();
    form.append(fieldName, compressed);
    for (const [key, value] of Object.entries(extraData)) {
      if (value != null) form.append(key, value);
    }
    return this.request("POST", path, form);
  }
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Singleton global
const api = new ApiClient();
