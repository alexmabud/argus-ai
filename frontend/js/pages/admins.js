/**
 * Página de gestão de admins — exclusiva do super-admin (dono).
 *
 * Permite promover um usuário a admin delegado (sem tirá-lo da equipe),
 * configurar por pessoa as 6 permissões granulares e rebaixar admins.
 * Promover/rebaixar e excluir usuários são exclusivos do super-admin —
 * por isso esta página só é acessível a is_super_admin.
 *
 * Nota: no backend a entidade chama-se "guarnicao"; na UI exibe-se "Equipe".
 */

//: Toggles granulares exibidos por admin (chave da flag → rótulo na UI).
const ADMIN_TOGGLES = [
  ["pode_criar_usuario", "Adicionar usuários"],
  ["pode_gerar_senha", "Gerar nova senha"],
  ["pode_pausar", "Pausar usuário"],
  ["pode_mover_equipe", "Mover de equipe"],
  ["pode_gerir_equipes", "Criar/editar equipes e BPMs"],
  ["admin_global", "Acesso a todas as equipes (global)"],
];

function renderAdmins() {
  const togglesHtml = ADMIN_TOGGLES.map(
    ([campo, rotulo]) => `
      <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-family: var(--font-data); font-size: 0.8125rem; color: var(--color-text-muted);">
        <input type="checkbox" x-model="a.${campo}" />
        <span>${rotulo}</span>
      </label>`
  ).join("");

  return `
    <div style="padding: 1rem;" x-data="adminsPage()" x-init="init()">
      <!-- Cabeçalho -->
      <div style="margin-bottom: 1rem;">
        <h2 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 1.125rem; text-transform: uppercase; letter-spacing: 0.05em;">GERENCIAR ADMINS</h2>
        <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.125rem;">Promova usuários a admin e defina as permissões de cada um</p>
      </div>

      <!-- Tornar admin -->
      <div class="glass-card" style="padding: 1rem; margin-bottom: 1rem;">
        <label class="login-field-label">Tornar usuário admin</label>
        <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.25rem;">
          <select x-model="novoAdminId" style="flex: 1; padding: 0.5rem; font-size: 0.8125rem; font-family: var(--font-data); background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
            <option value="">Selecionar usuário...</option>
            <template x-for="u in candidatos" :key="u.id">
              <option :value="u.id" x-text="nomeUsuario(u) + ' · ' + nomeEquipe(u.guarnicao_id)"></option>
            </template>
          </select>
          <button @click="tornarAdmin()" :disabled="!novoAdminId || salvando" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.5rem 0.75rem;">
            Tornar admin
          </button>
        </div>
        <p x-show="candidatos.length === 0 && !carregando" style="color: var(--color-text-dim); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.5rem;">
          Nenhum usuário disponível para promover.
        </p>
      </div>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Lista de admins -->
      <div x-show="!carregando" style="display: flex; flex-direction: column; gap: 0.75rem;">
        <template x-if="admins.length === 0">
          <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum admin cadastrado.</p>
        </template>

        <template x-for="a in admins" :key="a.id">
          <div class="glass-card" style="padding: 1rem;">
            <!-- Identidade -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
              <div style="min-width: 0;">
                <p style="color: var(--color-primary); font-family: var(--font-display); font-weight: 700; font-size: 0.9375rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" x-text="nomeUsuario(a)"></p>
                <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="a.matricula + ' · ' + nomeEquipe(a.guarnicao_id)"></p>
              </div>
              <span x-show="a.is_super_admin"
                    style="font-size: 0.6875rem; font-family: var(--font-data); font-weight: 600; color: #FFA500; background: rgba(255,165,0,0.12); border: 1px solid rgba(255,165,0,0.3); border-radius: 4px; padding: 0.125rem 0.5rem; flex-shrink: 0;">
                DONO
              </span>
            </div>

            <!-- Super-admin (você): sem edição -->
            <template x-if="a.is_super_admin">
              <p style="color: var(--color-text-dim); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.5rem;">
                Super-admin tem acesso total e não pode ser editado por aqui.
              </p>
            </template>

            <!-- Admin delegado: toggles + ações -->
            <template x-if="!a.is_super_admin">
              <div style="margin-top: 0.75rem;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.375rem 0.75rem; margin-bottom: 0.75rem;">
                  ${togglesHtml}
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <button @click="salvarPermissoes(a)" :disabled="salvando" class="btn btn-primary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                    Salvar permissões
                  </button>
                  <button @click="rebaixar(a)" :disabled="salvando"
                          style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.75rem; border-radius: 4px; background: rgba(255,107,0,0.15); color: var(--color-danger); border: 1px solid rgba(255,107,0,0.3); cursor: pointer;">
                    Rebaixar
                  </button>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>
    </div>
  `;
}

function adminsPage() {
  return {
    admins: [],
    usuarios: [],
    equipes: [],
    novoAdminId: "",
    carregando: true,
    salvando: false,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        const [admins, usuarios, equipes] = await Promise.all([
          api.get("/admin/admins"),
          api.get("/admin/usuarios"),
          api.get("/admin/equipes"),
        ]);
        this.admins = admins;
        this.usuarios = usuarios;
        this.equipes = equipes;
      } catch {
        showToast("Erro ao carregar admins", "error");
      } finally {
        this.carregando = false;
      }
    },

    /** Usuários elegíveis a promover: ativos que ainda não são admin/super. */
    get candidatos() {
      const adminIds = new Set(this.admins.map((a) => a.id));
      return this.usuarios.filter((u) => !adminIds.has(u.id));
    },

    nomeUsuario(u) {
      const posto =
        (typeof POSTO_ABREV !== "undefined" && POSTO_ABREV[u.posto_graduacao]) ||
        u.posto_graduacao ||
        "";
      const guerra = u.nome_guerra || (u.nome !== u.matricula ? u.nome : "") || u.matricula;
      return (posto ? posto + " " : "") + guerra;
    },

    nomeEquipe(guarnicaoId) {
      if (guarnicaoId === null || guarnicaoId === undefined) return "Sem equipe";
      const e = this.equipes.find((eq) => eq.id === guarnicaoId);
      return e ? e.nome : "Sem equipe";
    },

    _payload(a, isAdmin) {
      return {
        is_admin: isAdmin,
        pode_criar_usuario: !!a.pode_criar_usuario,
        pode_gerar_senha: !!a.pode_gerar_senha,
        pode_pausar: !!a.pode_pausar,
        pode_mover_equipe: !!a.pode_mover_equipe,
        pode_gerir_equipes: !!a.pode_gerir_equipes,
        admin_global: !!a.admin_global,
      };
    },

    async tornarAdmin() {
      if (!this.novoAdminId || this.salvando) return;
      this.salvando = true;
      try {
        await api.put(`/admin/usuarios/${parseInt(this.novoAdminId)}/admin`, {
          is_admin: true,
        });
        showToast("Usuário promovido a admin", "success");
        this.novoAdminId = "";
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao promover usuário", "error");
      } finally {
        this.salvando = false;
      }
    },

    async salvarPermissoes(a) {
      if (this.salvando) return;
      this.salvando = true;
      try {
        await api.put(`/admin/usuarios/${a.id}/admin`, this._payload(a, true));
        showToast("Permissões atualizadas", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao salvar permissões", "error");
      } finally {
        this.salvando = false;
      }
    },

    async rebaixar(a) {
      if (this.salvando) return;
      if (!confirm(`Remover ${a.matricula} da lista de admins?`)) return;
      this.salvando = true;
      try {
        await api.put(`/admin/usuarios/${a.id}/admin`, this._payload(a, false));
        showToast("Admin rebaixado", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao rebaixar admin", "error");
      } finally {
        this.salvando = false;
      }
    },
  };
}
