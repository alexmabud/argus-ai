/**
 * Cliente HTTP para API Argus AI.
 *
 * Gerencia requisições com retry exponencial, refresh automático
 * de token JWT e tratamento de rate limiting.
 */
class ApiClient {
  constructor() {
    this.baseUrl = "/api/v1";
    this.token = localStorage.getItem("argus_token");
    this.refreshToken = localStorage.getItem("argus_refresh_token");
    this._refreshPromise = null;
  }

  setTokens(access, refresh) {
    this.token = access;
    this.refreshToken = refresh;
    localStorage.setItem("argus_token", access);
    localStorage.setItem("argus_refresh_token", refresh);
  }

  clearTokens() {
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem("argus_token");
    localStorage.removeItem("argus_refresh_token");
    localStorage.removeItem("argus_user");
  }

  async request(method, path, body = null, retries = 2) {
    const url = `${this.baseUrl}${path}`;
    const headers = {};

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const options = { method, headers };

    if (body && !(body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
      options.body = body;
    }

    try {
      const response = await fetch(url, options);

      // Token expirado — tentar refresh
      if (response.status === 401 && !this.refreshToken) {
        // Sem refresh token: sessão inválida, forçar re-login
        this.clearTokens();
        window.dispatchEvent(new Event("auth:expired"));
        throw new ApiError(401, "Sessão expirada");
      }
      if (response.status === 401 && this.refreshToken) {
        const refreshResult = await this._refreshAccessToken();
        if (refreshResult === "ok") {
          headers["Authorization"] = `Bearer ${this.token}`;
          const retryResponse = await fetch(url, { ...options, headers });
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
        // refreshResult === "network_error" — rede instável, NÃO destruir tokens
        // Os tokens permanecem no localStorage para tentar novamente depois
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
          const response = await fetch(`${this.baseUrl}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: this.refreshToken }),
          });
          if (response.ok) {
            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);
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
      // Esgotou tentativas sem resposta do servidor — preservar tokens
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
