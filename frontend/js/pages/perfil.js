/**
 * Página de perfil do usuário.
 *
 * Permite atualizar nome, posto/graduação e foto.
 * Admins têm seção de configuração de 2FA TOTP.
 * Contém o botão Sair com aviso de nova senha necessária.
 */

const POSTOS_GRADUACAO = [
  "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento",
  "Subtenente", "Aspirante", "2º Tenente", "1º Tenente",
  "Capitão", "Major", "Tenente-Coronel", "Coronel",
];

function renderPerfil(_appState) {
  const user = auth.getUser() || {};
  const iniciais = (user.nome || "?")
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  const optsPosto = POSTOS_GRADUACAO.map(
    (p) => `<option value="${p}" ${user.posto_graduacao === p ? "selected" : ""}>${p}</option>`
  ).join("");

  return `
    <div style="padding: 16px; max-width: 448px; margin: 0 auto;" x-data="perfilPage()">
      <!-- Foto de perfil -->
      <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 24px;">
        <div style="position: relative;">
          <div style="width: 96px; height: 96px; border-radius: 4px; overflow: hidden; background: var(--color-surface-hover); border: 1px solid var(--color-primary); display: flex; align-items: center; justify-content: center; color: var(--color-primary); font-size: 28px; font-family: var(--font-display); font-weight: 700; cursor: pointer;"
               @click="$refs.fotoInput.click()">
            <template x-if="fotoUrl">
              <img :src="fotoUrl" style="width: 100%; height: 100%; object-fit: cover;" />
            </template>
            <template x-if="!fotoUrl">
              <span>${iniciais}</span>
            </template>
          </div>
          <button @click="$refs.fotoInput.click()"
                  style="position: absolute; bottom: -4px; right: -4px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 4px; color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center;"
                  class="hov-text">
            <svg xmlns="http://www.w3.org/2000/svg" style="width: 16px; height: 16px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </button>
        </div>
        <input type="file" accept="image/*" x-ref="fotoInput" class="hidden" @change="uploadFoto($event)" />
        <p x-show="uploadando" style="font-size: 12px; color: var(--color-text-muted); margin-top: 8px; font-family: var(--font-data);">Enviando foto...</p>
      </div>

      <!-- Campos de perfil -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div>
          <label class="login-field-label">Nome completo</label>
          <input type="text" class="input-upper" x-model="nome" />
        </div>

        <div>
          <label class="login-field-label">Nome de guerra</label>
          <input type="text" class="input-upper" x-model="nomeGuerra"
                 placeholder="Ex: Silva" maxlength="50" />
        </div>

        <div>
          <label class="login-field-label">Posto / Graduação</label>
          <select x-model="posto">
            <option value="">Selecione...</option>
            ${optsPosto}
          </select>
        </div>

        <div>
          <label class="login-field-label">Matrícula</label>
          <input type="text" value="${user.matricula || ""}" disabled
                 style="background: var(--color-bg); color: var(--color-text-dim); cursor: not-allowed;" />
        </div>

        <button @click="salvar()" :disabled="salvando" class="btn btn-primary" style="width: 100%;">
          <span x-show="!salvando">Salvar alterações</span>
          <span x-show="salvando">Salvando...</span>
        </button>

        <template x-if="isAdmin">
          <button @click="irParaAdmin()" class="btn btn-secondary" style="width: 100%; margin-top: 4px;">
            Gerenciar usuários
          </button>
        </template>

        <template x-if="isSuperAdmin">
          <button @click="irParaAdmins()" class="btn btn-secondary" style="width: 100%; margin-top: 4px;">
            Gerenciar admins
          </button>
        </template>

        <template x-if="isAdmin">
          <button @click="abrirDashboard()" class="btn btn-secondary" style="width: 100%; margin-top: 4px;">
            📊 Dashboard de Performance
          </button>
        </template>
      </div>

      <!-- Seção 2FA (somente admins) -->
      <template x-if="isAdmin">
        <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--color-border);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div>
              <p style="font-family: var(--font-display); font-weight: 600; font-size: 14px; color: var(--color-text); margin: 0;">Autenticação em 2 Fatores</p>
              <p style="font-family: var(--font-body); font-size: 12px; color: var(--color-text-muted); margin: 4px 0 0 0;">Google Authenticator ou Authy</p>
            </div>
            <span x-show="totp2fa.ativo"
                  style="font-size: 11px; font-family: var(--font-data); font-weight: 600; color: #22c55e; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 4px; padding: 2px 8px;">
              ATIVO
            </span>
            <span x-show="!totp2fa.ativo"
                  style="font-size: 11px; font-family: var(--font-data); font-weight: 600; color: var(--color-text-dim); background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 2px 8px;">
              INATIVO
            </span>
          </div>

          <!-- Botão configurar -->
          <template x-if="!totp2fa.uri">
            <button @click="totp2fa.configurar()" :disabled="totp2fa.carregando" class="btn btn-secondary" style="width: 100%;">
              <span x-show="!totp2fa.carregando" x-text="totp2fa.ativo ? 'Reconfigurar 2FA' : 'Configurar 2FA'"></span>
              <span x-show="totp2fa.carregando">Gerando QR Code...</span>
            </button>
          </template>

          <!-- QR Code + confirmação -->
          <template x-if="totp2fa.uri">
            <div style="display: flex; flex-direction: column; gap: 16px;">
              <p style="font-size: 12px; color: var(--color-text-muted); font-family: var(--font-body); margin: 0;">
                Escaneie o QR Code com o Google Authenticator ou Authy.
              </p>
              <div style="display: flex; justify-content: center;">
                <div id="totp-qrcode" style="background: #fff; padding: 12px; border-radius: 8px; display: inline-block;"></div>
              </div>
              <div>
                <p style="font-size: 11px; color: var(--color-text-dim); font-family: var(--font-data); margin: 0 0 4px 0;">Código manual:</p>
                <code style="font-size: 13px; color: var(--color-primary); font-family: var(--font-data); letter-spacing: 2px; word-break: break-all;" x-text="totp2fa.secret"></code>
              </div>
              <div>
                <label class="login-field-label">Digite o código do app para confirmar</label>
                <input type="text" inputmode="numeric" maxlength="6" placeholder="000000"
                       x-model="totp2fa.codigoConfirm"
                       style="letter-spacing: 4px; text-align: center; font-family: var(--font-data); font-size: 20px;"
                       @keydown.enter="totp2fa.confirmar()" />
              </div>
              <div style="display: flex; gap: 8px;">
                <button @click="totp2fa.cancelar()" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
                <button @click="totp2fa.confirmar()" :disabled="totp2fa.confirmando || totp2fa.codigoConfirm.length < 6" class="btn btn-primary" style="flex: 1;">
                  <span x-show="!totp2fa.confirmando">Confirmar</span>
                  <span x-show="totp2fa.confirmando">Verificando...</span>
                </button>
              </div>
            </div>
          </template>
        </div>
      </template>

      <!-- Botão Sair -->
      <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--color-border);">
        <button @click="mostrarModalSaida()"
                style="width: 100%; padding: 8px 16px; font-family: var(--font-data); font-size: 14px; font-weight: 500; color: var(--color-danger); background: transparent; border: 1px solid var(--color-danger); border-radius: 4px; cursor: pointer; transition: opacity 0.2s;"
                class="hov-opacity-down">
          Sair do aplicativo
        </button>
      </div>
    </div>
  `;
}

function perfilPage() {
  const user = auth.getUser() || {};
  return {
    nome: user.nome || "",
    nomeGuerra: user.nome_guerra || "",
    posto: user.posto_graduacao || "",
    fotoUrl: user.foto_url || null,
    salvando: false,
    uploadando: false,
    isAdmin: user.is_admin || user.is_super_admin || false,
    isSuperAdmin: user.is_super_admin || false,

    totp2fa: {
      ativo: user.totp_ativo || false,
      uri: null,
      secret: null,
      codigoConfirm: "",
      carregando: false,
      confirmando: false,

      async configurar() {
        this.carregando = true;
        try {
          const res = await api.post("/admin/2fa/setup", {});
          this.uri = res.uri;
          const match = /secret=([^&]+)/.exec(res.uri);
          this.secret = match ? match[1] : "";
          this.codigoConfirm = "";
          await this.$nextTick();
          this._renderQr();
        } catch (e) {
          showToast("Erro ao gerar QR Code", "error");
        } finally {
          this.carregando = false;
        }
      },

      _renderQr() {
        const el = document.getElementById("totp-qrcode");
        if (!el || !this.uri) return;
        el.innerHTML = "";
        new QRCode(el, { text: this.uri, width: 180, height: 180, correctLevel: QRCode.CorrectLevel.M });
      },

      async confirmar() {
        if (this.codigoConfirm.length < 6) return;
        this.confirmando = true;
        try {
          const res = await api.post("/admin/2fa/verify", { code: this.codigoConfirm });
          if (res.valido) {
            this.ativo = true;
            this.uri = null;
            this.secret = null;
            this.codigoConfirm = "";
            const updated = { ...auth.getUser(), totp_ativo: true };
            auth.user = updated;
            localStorage.setItem("argus_user", JSON.stringify(updated));
            showToast("2FA configurado com sucesso!", "success");
          } else {
            showToast("Código inválido. Verifique o app e tente novamente.", "error");
            this.codigoConfirm = "";
          }
        } catch (e) {
          showToast("Erro ao verificar código", "error");
        } finally {
          this.confirmando = false;
        }
      },

      cancelar() {
        this.uri = null;
        this.secret = null;
        this.codigoConfirm = "";
      },
    },

    async salvar() {
      this.salvando = true;
      try {
        const updated = await api.put("/auth/perfil", {
          nome: this.nome,
          nome_guerra: this.nomeGuerra || null,
          posto_graduacao: this.posto || null,
        });
        auth.user = updated;
        localStorage.setItem("argus_user", JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent("user:updated", { detail: updated }));
        showToast("Perfil atualizado com sucesso", "success");
      } catch (e) {
        showToast("Erro ao salvar perfil", "error");
      } finally {
        this.salvando = false;
      }
    },

    async uploadFoto(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.uploadando = true;
      try {
        const formData = new FormData();
        formData.append("foto", file);
        const result = await api.uploadForm("/auth/perfil/foto", formData);
        this.fotoUrl = result.foto_url;
        auth.user = { ...auth.getUser(), foto_url: result.foto_url };
        localStorage.setItem("argus_user", JSON.stringify(auth.user));
        window.dispatchEvent(new CustomEvent("user:updated", { detail: auth.user }));
        showToast("Foto atualizada", "success");
      } catch (e) {
        showToast("Erro ao enviar foto", "error");
      } finally {
        this.uploadando = false;
        event.target.value = "";
      }
    },

    irParaAdmin() {
      window.dispatchEvent(new CustomEvent("navigate", { detail: "admin-usuarios" }));
    },

    irParaAdmins() {
      window.dispatchEvent(new CustomEvent("navigate", { detail: "admins" }));
    },

    abrirDashboard() {
      window.open("/grafana", "_blank", "noopener,noreferrer");
    },

    mostrarModalSaida() {
      const isAdmin = this.isAdmin;
      const msg = isAdmin
        ? 'Você será desconectado. Poderá entrar novamente com sua senha de administrador.'
        : 'Se você sair, precisará que o administrador gere uma nova senha para acessar novamente.';

      const overlay = document.createElement('div');
      overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(5,10,15,0.85);display:flex;align-items:center;justify-content:center;z-index:9999;padding:16px;';
      overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

      overlay.innerHTML = `
        <div class="glass-card" style="padding:24px;max-width:384px;width:100%;border:1px solid var(--color-border);">
          <h3 style="color:var(--color-text);font-family:var(--font-display);font-weight:600;margin-bottom:8px;">Sair do aplicativo?</h3>
          <p style="color:var(--color-text-muted);font-size:14px;margin-bottom:24px;font-family:var(--font-body);">${msg}</p>
          <div style="display:flex;gap:12px;">
            <button id="modal-cancelar" class="btn btn-secondary" style="flex:1;">Cancelar</button>
            <button id="modal-confirmar" style="flex:1;padding:8px 16px;border-radius:4px;background:var(--color-danger);color:var(--color-text);font-family:var(--font-body);font-weight:500;border:none;cursor:pointer;">Confirmar saída</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
      overlay.querySelector('#modal-cancelar').addEventListener('click', () => overlay.remove());
      overlay.querySelector('#modal-confirmar').addEventListener('click', () => {
        overlay.remove();
        window.dispatchEvent(new CustomEvent("auth:logout"));
      });
    },
  };
}
