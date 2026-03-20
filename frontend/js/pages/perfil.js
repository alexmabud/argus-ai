/**
 * Página de perfil do usuário.
 *
 * Permite atualizar nome, posto/graduação e foto.
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
    <div style="padding: 1rem; max-width: 28rem; margin: 0 auto;" x-data="perfilPage()">
      <!-- Foto de perfil -->
      <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 1.5rem;">
        <div style="position: relative;">
          <div style="width: 96px; height: 96px; border-radius: 4px; overflow: hidden; background: var(--color-surface-hover); border: 1px solid var(--color-primary); display: flex; align-items: center; justify-content: center; color: var(--color-primary); font-size: 1.875rem; font-family: var(--font-display); font-weight: 700; cursor: pointer;"
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
                  onmouseover="this.style.color='var(--color-text)'"
                  onmouseout="this.style.color='var(--color-text-muted)'">
            <svg xmlns="http://www.w3.org/2000/svg" style="width: 16px; height: 16px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </button>
        </div>
        <input type="file" accept="image/*" x-ref="fotoInput" class="hidden" @change="uploadFoto($event)" />
        <p x-show="uploadando" style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: 0.5rem; font-family: var(--font-data);">Enviando foto...</p>
      </div>

      <!-- Campos de perfil -->
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label class="login-field-label">Nome completo</label>
          <input type="text" x-model="nome" />
        </div>

        <div>
          <label class="login-field-label">Nome de guerra</label>
          <input type="text" x-model="nomeGuerra"
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
          <button @click="irParaAdmin()" class="btn btn-secondary" style="width: 100%; margin-top: 0.25rem;">
            Gerenciar usuários
          </button>
        </template>
      </div>

      <!-- Botão Sair -->
      <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--color-border);">
        <button @click="confirmarSaida = true"
                style="width: 100%; padding: 0.5rem 1rem; font-family: var(--font-data); font-size: 0.875rem; font-weight: 500; color: var(--color-danger); background: transparent; border: 1px solid var(--color-danger); border-radius: 4px; cursor: pointer; transition: opacity 0.2s;"
                onmouseover="this.style.opacity='0.8'"
                onmouseout="this.style.opacity='1'">
          Sair do aplicativo
        </button>
      </div>

      <!-- Modal de confirmação de saída -->
      <div x-show="confirmarSaida" x-cloak
           @click.self="confirmarSaida = false"
           style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(5,10,15,0.85); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 1rem;">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid var(--color-border);">
          <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 0.5rem;">Sair do aplicativo?</h3>
          <p style="color: var(--color-text-muted); font-size: 0.875rem; margin-bottom: 1.5rem; font-family: var(--font-body);" x-text="isAdmin
            ? 'Você será desconectado. Poderá entrar novamente com sua senha de administrador.'
            : 'Se você sair, precisará que o administrador gere uma nova senha para acessar novamente.'">
          </p>
          <div style="display: flex; gap: 0.75rem;">
            <button @click="confirmarSaida = false" class="btn btn-secondary" style="flex: 1;">
              Cancelar
            </button>
            <button @click="executarSaida()"
                    style="flex: 1; padding: 0.5rem 1rem; border-radius: 4px; background: var(--color-danger); color: var(--color-text); font-family: var(--font-body); font-weight: 500; border: none; cursor: pointer; transition: opacity 0.2s;"
                    onmouseover="this.style.opacity='0.85'"
                    onmouseout="this.style.opacity='1'">
              Confirmar saída
            </button>
          </div>
        </div>
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
    confirmarSaida: false,
    isAdmin: user.is_admin || false,

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

    executarSaida() {
      window.dispatchEvent(new CustomEvent("auth:logout"));
    },
  };
}
