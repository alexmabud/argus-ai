/**
 * Página de gestão de usuários — exclusivo para administradores.
 *
 * Lista usuários da guarnição, permite criar novos (exibindo senha única),
 * pausar acesso e gerar nova senha.
 */

function renderAdminUsuarios() {
  return `
    <div style="padding: 1rem;" x-data="adminUsuariosPage()" x-init="init()">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <div>
          <h2 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 1.125rem; text-transform: uppercase; letter-spacing: 0.05em;">GERENCIAR USUARIOS</h2>
          <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.125rem;">Controle de acesso da guarnição</p>
        </div>
        <button @click="mostrarFormCriacao = true" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.375rem 0.75rem;">
          + Novo usuário
        </button>
      </div>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Lista -->
      <div x-show="!carregando" style="display: flex; flex-direction: column; gap: 0.75rem;">
        <template x-for="u in usuarios" :key="u.id">
          <div class="glass-card" style="padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <!-- Avatar -->
              <div style="width: 40px; height: 40px; border-radius: 4px; background: var(--color-surface-hover); border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-primary); font-size: 0.875rem; font-family: var(--font-display); font-weight: 700; overflow: hidden; flex-shrink: 0;">
                <template x-if="u.foto_url">
                  <img :src="u.foto_url" style="width: 100%; height: 100%; object-fit: cover;" />
                </template>
                <template x-if="!u.foto_url">
                  <span x-text="(u.nome || '?').split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase()"></span>
                </template>
              </div>
              <!-- Info -->
              <div style="flex: 1; min-width: 0;">
                <p style="color: var(--color-text); font-family: var(--font-body); font-weight: 500; font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" x-text="u.nome"></p>
                <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="u.matricula + (u.posto_graduacao ? ' · ' + u.posto_graduacao : '')"></p>
              </div>
              <!-- Status -->
              <span :style="u.tem_sessao
                ? 'background: rgba(0,255,136,0.15); color: var(--color-success);'
                : 'background: rgba(58,80,104,0.3); color: var(--color-text-dim);'"
                    style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.125rem 0.5rem; border-radius: 4px; flex-shrink: 0;">
                <span x-text="u.tem_sessao ? 'Ativo' : 'Sem sessão'"></span>
              </span>
            </div>
            <!-- Ações -->
            <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
              <button @click="pausarUsuario(u)"
                      x-show="u.tem_sessao"
                      style="flex: 1; font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.5rem; border-radius: 4px; background: rgba(255,165,0,0.15); color: #FFA500; border: 1px solid rgba(255,165,0,0.3); cursor: pointer; transition: opacity 0.2s;"
                      onmouseover="this.style.opacity='0.8'"
                      onmouseout="this.style.opacity='1'">
                Pausar acesso
              </button>
              <button @click="gerarSenha(u)" class="btn btn-secondary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                Gerar nova senha
              </button>
              <button @click="excluirUsuario(u)"
                      style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.75rem; border-radius: 4px; background: rgba(255,107,0,0.15); color: var(--color-danger); border: 1px solid rgba(255,107,0,0.3); cursor: pointer; transition: opacity 0.2s;"
                      onmouseover="this.style.opacity='0.8'"
                      onmouseout="this.style.opacity='1'">
                Excluir
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Modal: Criar usuário -->
      <div x-show="mostrarFormCriacao" x-cloak
           style="position: fixed; inset: 0; background: rgba(5,10,15,0.8); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 1rem;">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid var(--color-border);">
          <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Novo usuário</h3>
          <div style="margin-bottom: 1rem;">
            <label class="login-field-label">Matrícula</label>
            <input type="text" x-model="novaMatricula"
                   placeholder="Ex: PM001" />
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button @click="mostrarFormCriacao = false; novaMatricula = ''" class="btn btn-secondary" style="flex: 1;">
              Cancelar
            </button>
            <button @click="criarUsuario()" :disabled="criando" class="btn btn-primary" style="flex: 1;">
              <span x-show="!criando">Criar</span>
              <span x-show="criando">Criando...</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: Exibir senha gerada (uso único) -->
      <div x-show="senhaGerada" x-cloak
           style="position: fixed; inset: 0; background: rgba(5,10,15,0.8); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 1rem;">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid #FFA500;">
          <h3 style="color: #FFA500; font-family: var(--font-display); font-weight: 600; margin-bottom: 0.5rem;">Senha gerada — anote agora</h3>
          <p style="color: var(--color-text-muted); font-family: var(--font-body); font-size: 0.875rem; margin-bottom: 1rem;">
            Esta senha será exibida apenas uma vez. Entregue pessoalmente ao usuário.
          </p>
          <div style="background: var(--color-bg); border-radius: 4px; padding: 1rem; text-align: center; margin-bottom: 1rem; border: 1px solid var(--color-border);">
            <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-bottom: 0.25rem;" x-text="'Matrícula: ' + (senhaGerada?.matricula || '')"></p>
            <p style="color: var(--color-text); font-family: var(--font-data); font-size: 1.5rem; font-weight: 700; letter-spacing: 0.1em;" x-text="senhaGerada?.senha"></p>
          </div>
          <button @click="senhaGerada = null" class="btn btn-secondary" style="width: 100%;">
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
    excluindo: false,
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
      if (this.excluindo) return;
      if (!confirm(`Excluir o usuário ${u.matricula}? Esta ação não pode ser desfeita.`)) return;
      this.excluindo = true;
      try {
        await api.delete(`/admin/usuarios/${u.id}`);
        showToast("Usuário excluído", "success");
        await this.carregar();
      } catch {
        showToast("Erro ao excluir usuário", "error");
      } finally {
        this.excluindo = false;
      }
    },
  };
}
