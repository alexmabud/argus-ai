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
      if (response.status === 401 && this.refreshToken) {
        const refreshed = await this._refreshAccessToken();
        if (refreshed) {
          headers["Authorization"] = `Bearer ${this.token}`;
          const retryResponse = await fetch(url, { ...options, headers });
          if (retryResponse.ok) return await retryResponse.json();
          throw new ApiError(retryResponse.status, await retryResponse.text());
        }
        // Refresh falhou — limpar tokens
        this.clearTokens();
        window.dispatchEvent(new Event("auth:expired"));
        throw new ApiError(401, "Sessão expirada");
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
        throw new ApiError(response.status, errorData.detail || "Erro na requisição");
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

  async _refreshAccessToken() {
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      this.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  get(path) { return this.request("GET", path); }
  post(path, body) { return this.request("POST", path, body); }
  put(path, body) { return this.request("PUT", path, body); }
  del(path) { return this.request("DELETE", path); }

  async uploadFile(path, file, extraData = {}) {
    const form = new FormData();
    form.append("file", file);
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
