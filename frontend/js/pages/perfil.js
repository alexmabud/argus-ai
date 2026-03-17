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
    <div class="p-4 max-w-md mx-auto" x-data="perfilPage()">
      <!-- Foto de perfil -->
      <div class="flex flex-col items-center mb-6">
        <div class="relative">
          <div class="w-24 h-24 rounded-full overflow-hidden bg-blue-600 flex items-center justify-center text-white text-3xl font-bold cursor-pointer"
               @click="$refs.fotoInput.click()">
            <template x-if="fotoUrl">
              <img :src="fotoUrl" class="w-full h-full object-cover" />
            </template>
            <template x-if="!fotoUrl">
              <span>${iniciais}</span>
            </template>
          </div>
          <button @click="$refs.fotoInput.click()"
                  class="absolute bottom-0 right-0 bg-slate-700 rounded-full p-1 text-slate-300 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </button>
        </div>
        <input type="file" accept="image/*" x-ref="fotoInput" class="hidden" @change="uploadFoto($event)" />
        <p x-show="uploadando" class="text-xs text-slate-400 mt-2">Enviando foto...</p>
      </div>

      <!-- Campos de perfil -->
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-slate-400 mb-1">Nome completo</label>
          <input type="text" x-model="nome"
                 class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none" />
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Nome de guerra</label>
          <input type="text" x-model="nomeGuerra"
                 class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none"
                 placeholder="Ex: Silva" maxlength="50" />
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Posto / Graduação</label>
          <select x-model="posto"
                  class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none">
            <option value="">Selecione...</option>
            ${optsPosto}
          </select>
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Matrícula</label>
          <input type="text" value="${user.matricula || ""}" disabled
                 class="w-full bg-slate-800 rounded-lg px-3 py-2 text-slate-400 border border-slate-700 cursor-not-allowed" />
        </div>

        <button @click="salvar()" :disabled="salvando"
                class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition">
          <span x-show="!salvando">Salvar alterações</span>
          <span x-show="salvando">Salvando...</span>
        </button>

        <template x-if="isAdmin">
          <button @click="irParaAdmin()"
                  class="w-full mt-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium py-2 rounded-lg transition">
            Gerenciar usuários
          </button>
        </template>
      </div>

      <!-- Botão Sair -->
      <div class="mt-8 pt-6 border-t border-slate-700">
        <button @click="confirmarSaida = true"
                class="w-full text-red-400 hover:text-red-300 text-sm font-medium py-2 border border-red-800 hover:border-red-600 rounded-lg transition">
          Sair do aplicativo
        </button>
      </div>

      <!-- Modal de confirmação de saída -->
      <div x-show="confirmarSaida" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-slate-700">
          <h3 class="text-white font-semibold mb-2">Sair do aplicativo?</h3>
          <p class="text-slate-400 text-sm mb-6" x-text="isAdmin
            ? 'Você será desconectado. Poderá entrar novamente com sua senha de administrador.'
            : 'Se você sair, precisará que o administrador gere uma nova senha para acessar novamente.'">
          </p>
          <div class="flex gap-3">
            <button @click="confirmarSaida = false"
                    class="flex-1 py-2 rounded-lg border border-slate-600 text-slate-300 hover:text-white">
              Cancelar
            </button>
            <button @click="executarSaida()"
                    class="flex-1 py-2 rounded-lg bg-red-700 hover:bg-red-600 text-white font-medium">
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
