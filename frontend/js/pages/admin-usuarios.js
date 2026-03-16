/**
 * Página de gestão de usuários — exclusivo para administradores.
 *
 * Lista usuários da guarnição, permite criar novos (exibindo senha única),
 * pausar acesso e gerar nova senha.
 */

function renderAdminUsuarios() {
  return `
    <div class="p-4" x-data="adminUsuariosPage()" x-init="init()">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-white font-semibold text-lg">Gerenciar Usuários</h2>
        <button @click="mostrarFormCriacao = true"
                class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded-lg">
          + Novo usuário
        </button>
      </div>

      <!-- Loading -->
      <div x-show="carregando" class="text-slate-400 text-sm text-center py-8">Carregando...</div>

      <!-- Lista -->
      <div x-show="!carregando" class="space-y-3">
        <template x-for="u in usuarios" :key="u.id">
          <div class="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div class="flex items-center gap-3">
              <!-- Avatar -->
              <div class="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white text-sm font-bold overflow-hidden flex-shrink-0">
                <template x-if="u.foto_url">
                  <img :src="u.foto_url" class="w-full h-full object-cover" />
                </template>
                <template x-if="!u.foto_url">
                  <span x-text="u.nome.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase()"></span>
                </template>
              </div>
              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p class="text-white font-medium text-sm truncate" x-text="u.nome"></p>
                <p class="text-slate-400 text-xs" x-text="u.matricula + (u.posto_graduacao ? ' · ' + u.posto_graduacao : '')"></p>
              </div>
              <!-- Status -->
              <span :class="u.tem_sessao ? 'bg-green-900 text-green-300' : 'bg-slate-700 text-slate-400'"
                    class="text-xs px-2 py-0.5 rounded-full flex-shrink-0">
                <span x-text="u.tem_sessao ? 'Ativo' : 'Sem sessão'"></span>
              </span>
            </div>
            <!-- Ações -->
            <div class="flex gap-2 mt-3">
              <button @click="pausarUsuario(u)"
                      x-show="u.tem_sessao"
                      class="flex-1 text-xs py-1.5 rounded-lg bg-yellow-900 text-yellow-300 hover:bg-yellow-800">
                Pausar acesso
              </button>
              <button @click="gerarSenha(u)"
                      class="flex-1 text-xs py-1.5 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600">
                Gerar nova senha
              </button>
              <button @click="excluirUsuario(u)"
                      class="text-xs py-1.5 px-3 rounded-lg bg-red-900 text-red-300 hover:bg-red-800">
                Excluir
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Modal: Criar usuário -->
      <div x-show="mostrarFormCriacao" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-slate-700">
          <h3 class="text-white font-semibold mb-4">Novo usuário</h3>
          <div class="mb-4">
            <label class="block text-sm text-slate-400 mb-1">Matrícula</label>
            <input type="text" x-model="novaMatricula"
                   class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none"
                   placeholder="Ex: PM001" />
          </div>
          <div class="flex gap-3">
            <button @click="mostrarFormCriacao = false; novaMatricula = ''"
                    class="flex-1 py-2 rounded-lg border border-slate-600 text-slate-300">
              Cancelar
            </button>
            <button @click="criarUsuario()" :disabled="criando"
                    class="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium">
              <span x-show="!criando">Criar</span>
              <span x-show="criando">Criando...</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: Exibir senha gerada (uso único) -->
      <div x-show="senhaGerada" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-yellow-700">
          <h3 class="text-yellow-400 font-semibold mb-2">Senha gerada — anote agora</h3>
          <p class="text-slate-400 text-sm mb-4">
            Esta senha será exibida apenas uma vez. Entregue pessoalmente ao usuário.
          </p>
          <div class="bg-slate-900 rounded-lg p-4 text-center mb-4">
            <p class="text-slate-400 text-xs mb-1" x-text="'Matrícula: ' + (senhaGerada?.matricula || '')"></p>
            <p class="text-white font-mono text-2xl font-bold tracking-widest" x-text="senhaGerada?.senha"></p>
          </div>
          <button @click="senhaGerada = null"
                  class="w-full py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white">
            Entendi, já anotei
          </button>
        </div>
      </div>
    </div>
  `;
}

function adminUsuariosPage() {
  return {
    usuarios: [],
    carregando: true,
    mostrarFormCriacao: false,
    novaMatricula: "",
    criando: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        this.usuarios = await api.get("/admin/usuarios");
      } catch {
        showToast("Erro ao carregar usuários", "error");
      } finally {
        this.carregando = false;
      }
    },

    async criarUsuario() {
      if (!this.novaMatricula.trim()) return;
      this.criando = true;
      try {
        const result = await api.post("/admin/usuarios", { matricula: this.novaMatricula.trim() });
        this.senhaGerada = result;
        this.mostrarFormCriacao = false;
        this.novaMatricula = "";
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao criar usuário", "error");
      } finally {
        this.criando = false;
      }
    },

    async pausarUsuario(u) {
      try {
        await api.patch(`/admin/usuarios/${u.id}/pausar`);
        showToast(`Acesso de ${u.matricula} pausado`, "success");
        await this.carregar();
      } catch {
        showToast("Erro ao pausar usuário", "error");
      }
    },

    async gerarSenha(u) {
      try {
        const result = await api.post(`/admin/usuarios/${u.id}/gerar-senha`);
        this.senhaGerada = result;
        await this.carregar();
      } catch {
        showToast("Erro ao gerar senha", "error");
      }
    },

    async excluirUsuario(u) {
      if (!confirm(`Excluir o usuário ${u.matricula}? Esta ação não pode ser desfeita.`)) return;
      try {
        await api.delete(`/admin/usuarios/${u.id}`);
        showToast("Usuário excluído", "success");
        await this.carregar();
      } catch {
        showToast("Erro ao excluir usuário", "error");
      }
    },
  };
}
