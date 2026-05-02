/**
 * Página de gestão de usuários e equipes — exclusivo para administradores.
 *
 * Organiza usuários em abas por equipe. A aba "Sem Equipe" lista usuários
 * sem guarnicao_id. Cada aba de equipe tem toggle de isolamento de abordagens
 * e permite mover usuários entre equipes. Aba "+ Nova Equipe" cria nova.
 *
 * Nota: no backend a entidade chama-se "guarnicao". Na UI exibe-se "Equipe".
 */

function renderAdminUsuarios() {
  return `
    <div style="padding: 1rem;" x-data="adminUsuariosPage()" x-init="init()">
      <!-- Cabeçalho -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <div>
          <h2 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 1.125rem; text-transform: uppercase; letter-spacing: 0.05em;">GERENCIAR USUÁRIOS</h2>
          <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.125rem;">Equipes e acesso</p>
          <p x-show="!carregando" style="font-family: var(--font-data); font-size: 12px; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; white-space: nowrap;">
            Policiais Cadastrados:
            <span x-text="usuarios.length.toLocaleString('pt-BR')"
                  style="color: var(--color-success); font-size: 14px; font-weight: 700; text-shadow: 0 0 8px rgba(0,255,136,0.7), 0 0 20px rgba(0,255,136,0.35);"></span>
          </p>
        </div>
        <button @click="abrirCriarUsuario()" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.375rem 0.75rem;">
          + Novo usuário
        </button>
      </div>

      <!-- Abas -->
      <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 1rem; border-bottom: 1px solid var(--color-border);">
        <button
          @click="abaAtiva = 'sem-equipe'"
          :style="abaAtiva === 'sem-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          Sem Equipe (<span x-text="usuariosSemEquipe.length"></span>)
        </button>
        <template x-for="e in equipes" :key="e.id">
          <button
            @click="abaAtiva = e.id"
            :style="abaAtiva === e.id ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
            style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
            x-text="e.nome + ' (' + usuariosDaEquipe(e.id).length + ')'"
          ></button>
        </template>
        <button
          @click="abaAtiva = 'nova-equipe'"
          :style="abaAtiva === 'nova-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          + Nova Equipe
        </button>
      </div>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Conteúdo das abas -->
      <div x-show="!carregando">
        <!-- Aba: Sem Equipe -->
        <template x-if="abaAtiva === 'sem-equipe'">
          <div>
            <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-bottom: 0.75rem;">
              Usuários ainda não atribuídos a uma equipe.
            </p>
            <template x-if="usuariosSemEquipe.length === 0">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário sem equipe.</p>
            </template>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <template x-for="u in usuariosSemEquipe" :key="u.id">
                <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '' }">
                  ${cardUsuario('u')}
                  <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: center;">
                    <select x-model="destinoId" style="flex: 1; padding: 0.375rem 0.5rem; font-size: 0.75rem; font-family: var(--font-data); background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
                      <option value="">Selecionar equipe...</option>
                      <template x-for="e in equipes" :key="e.id">
                        <option :value="e.id" x-text="e.nome"></option>
                      </template>
                    </select>
                    <button @click="moverUsuario(u.id, destinoId ? parseInt(destinoId) : null); destinoId = ''" :disabled="!destinoId" class="btn btn-primary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                      Atribuir
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- Aba: Equipe específica -->
        <template x-if="abaAtiva !== 'sem-equipe' && abaAtiva !== 'nova-equipe'">
          <div>
            <template x-if="equipeAtiva">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-bottom: 0.75rem;">
                <div>
                  <p style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 0.9375rem;" x-text="equipeAtiva.nome"></p>
                  <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="equipeAtiva.unidade"></p>
                </div>
                <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                  <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens da equipe</span>
                  <input
                    type="checkbox"
                    :checked="equipeAtiva.isolamento_abordagens"
                    @change="alternarIsolamento(equipeAtiva.id, $event.target.checked)"
                  />
                </label>
              </div>
            </template>
            <template x-if="usuariosDaEquipe(abaAtiva).length === 0">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário nesta equipe.</p>
            </template>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <template x-for="u in usuariosDaEquipe(abaAtiva)" :key="u.id">
                <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '', modalMover: false }">
                  ${cardUsuario('u')}
                  <!-- Ações comuns -->
                  <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                    <button @click="pausarUsuario(u)"
                            x-show="u.tem_sessao"
                            style="flex: 1; font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.5rem; border-radius: 4px; background: rgba(255,165,0,0.15); color: #FFA500; border: 1px solid rgba(255,165,0,0.3); cursor: pointer;">
                      Pausar acesso
                    </button>
                    <button @click="gerarSenha(u)" class="btn btn-secondary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                      Gerar nova senha
                    </button>
                    <button @click="modalMover = true" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                      Mover
                    </button>
                    <button @click="excluirUsuario(u)"
                            style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.75rem; border-radius: 4px; background: rgba(255,107,0,0.15); color: var(--color-danger); border: 1px solid rgba(255,107,0,0.3); cursor: pointer;">
                      Excluir
                    </button>
                  </div>
                  <!-- Modal: Mover de equipe -->
                  <div x-show="modalMover"
                       @click.self="modalMover = false; destinoId = ''"
                       style="position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                    <div class="glass-card" style="padding: 1.5rem; min-width: 22rem; max-width: 90vw;">
                      <h4 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Mover policial</h4>
                      <select x-model="destinoId" style="width: 100%; padding: 0.5rem; font-size: 0.875rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text); border-radius: 4px; margin-bottom: 1rem;">
                        <option value="">Selecionar equipe destino...</option>
                        <option value="null">Sem equipe</option>
                        <template x-for="e in equipes.filter(eq => eq.id !== u.guarnicao_id)" :key="e.id">
                          <option :value="e.id" x-text="e.nome"></option>
                        </template>
                      </select>
                      <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button @click="modalMover = false; destinoId = ''" class="btn btn-secondary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                          Cancelar
                        </button>
                        <button @click="moverUsuario(u.id, destinoId === 'null' ? null : (destinoId ? parseInt(destinoId) : undefined)); destinoId = ''; modalMover = false"
                                :disabled="!destinoId"
                                class="btn btn-primary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                          Mover
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- Aba: Nova Equipe -->
        <template x-if="abaAtiva === 'nova-equipe'">
          <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
            <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Nova equipe</h3>
            <div style="margin-bottom: 0.75rem;">
              <label class="login-field-label">Nome</label>
              <input type="text" x-model="novaEquipe.nome" placeholder="Ex: 3ª Cia - GU 01" />
            </div>
            <div style="margin-bottom: 1rem;">
              <label class="login-field-label">Unidade</label>
              <input type="text" x-model="novaEquipe.unidade" placeholder="Ex: 3º BPM" />
            </div>
            <button @click="criarEquipe()" :disabled="criandoEquipe || !novaEquipe.nome || !novaEquipe.unidade" class="btn btn-primary" style="width: 100%;">
              <span x-show="!criandoEquipe">Criar equipe</span>
              <span x-show="criandoEquipe">Criando...</span>
            </button>
          </div>
        </template>
      </div>

      <!-- Modal: Criar usuário -->
      <div x-cloak
           :style="mostrarFormCriacao ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.8);align-items:center;justify-content:center;z-index:50;padding:1rem;' : 'display:none;'">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid var(--color-border);">
          <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Novo usuário</h3>
          <div style="margin-bottom: 0.75rem;">
            <label class="login-field-label">Matrícula</label>
            <input type="text" x-model="novaMatricula" placeholder="Ex: PM001" />
          </div>
          <div style="margin-bottom: 1rem;">
            <label class="login-field-label">Equipe</label>
            <select x-model="novaEquipeId" style="width: 100%; padding: 0.5rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
              <option value="">Sem equipe</option>
              <template x-for="e in equipes" :key="e.id">
                <option :value="e.id" x-text="e.nome"></option>
              </template>
            </select>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button @click="cancelarCriacao()" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
            <button @click="criarUsuario()" :disabled="criando" class="btn btn-primary" style="flex: 1;">
              <span x-show="!criando">Criar</span>
              <span x-show="criando">Criando...</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: senha gerada -->
      <div x-cloak
           :style="senhaGerada ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.8);align-items:center;justify-content:center;z-index:50;padding:1rem;' : 'display:none;'">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid #FFA500;">
          <h3 style="color: #FFA500; font-family: var(--font-display); font-weight: 600; margin-bottom: 0.5rem;">Senha gerada — anote agora</h3>
          <p style="color: var(--color-text-muted); font-family: var(--font-body); font-size: 0.875rem; margin-bottom: 1rem;">Esta senha será exibida apenas uma vez.</p>
          <div style="background: var(--color-bg); border-radius: 4px; padding: 1rem; text-align: center; margin-bottom: 1rem; border: 1px solid var(--color-border);">
            <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-bottom: 0.25rem;" x-text="'Matrícula: ' + (senhaGerada?.matricula || '')"></p>
            <p style="color: var(--color-text); font-family: var(--font-data); font-size: 1.5rem; font-weight: 700; letter-spacing: 0.1em;" x-text="senhaGerada?.senha"></p>
          </div>
          <button @click="senhaGerada = null" class="btn btn-secondary" style="width: 100%;">Entendi, já anotei</button>
        </div>
      </div>
    </div>
  `;
}

/** Helper que retorna o trecho de cabeçalho do card de usuário (avatar + info). */
function cardUsuario(varName) {
  return `
    <div style="display: flex; align-items: center; gap: 0.75rem;">
      <div style="width: 44px; height: 44px; border-radius: 4px; background: var(--color-surface-hover); border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-primary); font-size: 1rem; font-family: var(--font-display); font-weight: 700; overflow: hidden; flex-shrink: 0;">
        <template x-if="${varName}.foto_url">
          <img :src="${varName}.foto_url" style="width: 100%; height: 100%; object-fit: cover;" />
        </template>
        <template x-if="!${varName}.foto_url">
          <span x-text="(${varName}.nome_guerra || ${varName}.nome || '?')[0].toUpperCase()"></span>
        </template>
      </div>
      <div style="flex: 1; min-width: 0;">
        <p style="color: var(--color-primary); font-family: var(--font-display); font-weight: 700; font-size: 0.9375rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
           x-text="(POSTO_ABREV[${varName}.posto_graduacao] || ${varName}.posto_graduacao || 'Sem grad.') + (${varName}.nome_guerra ? ' ' + ${varName}.nome_guerra : '')"></p>
        <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
           x-text="(${varName}.nome !== ${varName}.matricula ? ${varName}.nome + ' · ' : '') + ${varName}.matricula"></p>
      </div>
      <span :style="${varName}.tem_sessao ? 'background: rgba(0,255,136,0.15); color: var(--color-success);' : 'background: rgba(58,80,104,0.3); color: var(--color-text-dim);'"
            style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.125rem 0.5rem; border-radius: 4px; flex-shrink: 0;"
            x-text="${varName}.tem_sessao ? 'Ativo' : 'Sem sessão'"></span>
    </div>
  `;
}

function adminUsuariosPage() {
  return {
    usuarios: [],
    equipes: [],
    abaAtiva: "sem-equipe",
    carregando: true,
    mostrarFormCriacao: false,
    novaMatricula: "",
    novaEquipeId: "",
    criando: false,
    novaEquipe: { nome: "", unidade: "" },
    criandoEquipe: false,
    excluindo: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        const [usuarios, equipes] = await Promise.all([
          api.get("/admin/usuarios"),
          api.get("/admin/equipes"),
        ]);
        const ordemRank = [
          "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento", "Subtenente",
          "Aspirante", "2º Tenente", "1º Tenente", "Capitão", "Major", "Tenente-Coronel", "Coronel",
        ];
        this.usuarios = usuarios.sort((a, b) => {
          const ra = ordemRank.indexOf(a.posto_graduacao ?? "");
          const rb = ordemRank.indexOf(b.posto_graduacao ?? "");
          if (rb !== ra) return rb - ra;
          return (parseInt(a.matricula) || 0) - (parseInt(b.matricula) || 0);
        });
        this.equipes = equipes;
        if (typeof this.abaAtiva === "number" && !this.equipes.some(e => e.id === this.abaAtiva)) {
          this.abaAtiva = "sem-equipe";
        }
      } catch {
        showToast("Erro ao carregar dados", "error");
      } finally {
        this.carregando = false;
      }
    },

    get usuariosSemEquipe() {
      return this.usuarios.filter(u => u.guarnicao_id === null || u.guarnicao_id === undefined);
    },

    usuariosDaEquipe(equipeId) {
      return this.usuarios.filter(u => u.guarnicao_id === equipeId);
    },

    get equipeAtiva() {
      return this.equipes.find(e => e.id === this.abaAtiva) || null;
    },

    abrirCriarUsuario() {
      this.novaMatricula = "";
      this.novaEquipeId = typeof this.abaAtiva === "number" ? String(this.abaAtiva) : "";
      this.mostrarFormCriacao = true;
    },

    cancelarCriacao() {
      this.mostrarFormCriacao = false;
      this.novaMatricula = "";
      this.novaEquipeId = "";
    },

    async criarUsuario() {
      if (!this.novaMatricula.trim()) return;
      this.criando = true;
      try {
        const payload = { matricula: this.novaMatricula.trim() };
        if (this.novaEquipeId) payload.guarnicao_id = parseInt(this.novaEquipeId);
        const result = await api.post("/admin/usuarios", payload);
        this.senhaGerada = result;
        this.cancelarCriacao();
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

    async moverUsuario(usuarioId, destinoId) {
      if (destinoId === undefined) return;
      try {
        await api.patch(`/admin/usuarios/${usuarioId}/equipe`, { guarnicao_id: destinoId });
        showToast("Usuário movido", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao mover usuário", "error");
      }
    },

    async criarEquipe() {
      if (!this.novaEquipe.nome.trim() || !this.novaEquipe.unidade.trim()) return;
      this.criandoEquipe = true;
      try {
        const equipe = await api.post("/admin/equipes", {
          nome: this.novaEquipe.nome.trim(),
          unidade: this.novaEquipe.unidade.trim(),
        });
        this.novaEquipe = { nome: "", unidade: "" };
        await this.carregar();
        this.abaAtiva = equipe.id;
      } catch (e) {
        showToast(e.message || "Erro ao criar equipe", "error");
      } finally {
        this.criandoEquipe = false;
      }
    },

    async alternarIsolamento(equipeId, valor) {
      try {
        await api.patch(`/admin/equipes/${equipeId}/toggle-isolamento`, {
          isolamento_abordagens: valor,
        });
        showToast(valor ? "Isolamento ativado" : "Isolamento desativado", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao atualizar equipe", "error");
        await this.carregar();
      }
    },
  };
}
