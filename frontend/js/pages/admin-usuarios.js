/**
 * Página de gestão de usuários e equipes — exclusivo para administradores.
 *
 * Navegação em 2 níveis: BPMs no topo (nível 1), equipes dentro do BPM
 * ativo (nível 2). A aba "Sem Equipe" (global) lista usuários sem guarnicao_id.
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
        <button @click="abrirCriarUsuario()" x-show="podeCriar" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.375rem 0.75rem;">
          + Novo usuário
        </button>
      </div>

      <!-- Nível 1: abas por BPM -->
      <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 0; border-bottom: 1px solid var(--color-border); background: rgba(0, 212, 255, 0.04); padding: 0 0.5rem;">
        <button
          @click="abaAtiva = 'sem-equipe'; bpmAtivo = null; equipeAtiva = null"
          :style="abaAtiva === 'sem-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          Sem Equipe (<span x-text="usuariosSemEquipe.length"></span>)
        </button>
        <template x-for="b in bpms" :key="b.id">
          <button
            @click="selecionarBpm(b.id)"
            :style="bpmAtivo === b.id ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
            style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
            x-text="b.nome + ' (' + usuariosDoBpm(b.id).length + ')'"
          ></button>
        </template>
        <button
          x-show="podeGerirEquipes"
          @click="abaAtiva = 'novo-bpm'; bpmAtivo = null; equipeAtiva = null"
          :style="abaAtiva === 'novo-bpm' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          + Novo BPM
        </button>
      </div>

      <!-- Nível 2: abas de equipes dentro do BPM ativo -->
      <template x-if="bpmAtivo !== null">
        <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 1rem; border-bottom: 1px solid rgba(58,80,104,0.4); background: rgba(26, 41, 64, 0.45); padding: 0.125rem 1rem;">
          <template x-for="e in equipesDoBpm(bpmAtivo)" :key="e.id">
            <button
              @click="equipeAtiva = e.id"
              :style="equipeAtiva === e.id ? 'border-bottom: 2px solid #4FC3F7; color: #4FC3F7;' : 'color: var(--color-text-muted);'"
              style="padding: 0.375rem 0.625rem; font-family: var(--font-data); font-size: 0.75rem; background: transparent; border: 0; cursor: pointer;"
              x-text="e.nome + ' (' + usuariosDaEquipe(e.id).length + ')'"
            ></button>
          </template>
          <button
            x-show="podeGerirEquipes"
            @click="equipeAtiva = 'nova-equipe'"
            :style="equipeAtiva === 'nova-equipe' ? 'border-bottom: 2px solid #4FC3F7; color: #4FC3F7;' : 'color: var(--color-text-muted);'"
            style="padding: 0.375rem 0.625rem; font-family: var(--font-data); font-size: 0.75rem; background: transparent; border: 0; cursor: pointer;"
          >
            + Nova Equipe
          </button>
        </div>
      </template>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Conteúdo -->
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
                  <div x-show="podeMover" style="display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: center;">
                    <select x-model="destinoId" style="flex: 1; padding: 0.375rem 0.5rem; font-size: 0.75rem; font-family: var(--font-data); background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
                      <option value="">Selecionar equipe...</option>
                      <template x-for="e in equipes" :key="e.id">
                        <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
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

        <!-- Aba: Novo BPM -->
        <template x-if="abaAtiva === 'novo-bpm'">
          <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
            <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Novo BPM</h3>
            <div style="margin-bottom: 1rem;">
              <label class="login-field-label">Nome</label>
              <input type="text" x-model="novoBpm.nome" placeholder="Ex: 14º BPM" />
            </div>
            <button @click="criarBpm()" :disabled="criandoBpm || !novoBpm.nome" class="btn btn-primary" style="width: 100%;">
              <span x-show="!criandoBpm">Criar BPM</span>
              <span x-show="criandoBpm">Criando...</span>
            </button>
          </div>
        </template>

        <!-- BPM selecionado: conteúdo de equipe -->
        <template x-if="bpmAtivo !== null">
          <div>

            <!-- Toggle de isolamento por BPM -->
            <template x-if="bpmAtivoObj">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; padding: 0.5rem 0.75rem; background: rgba(0,0,0,0.15); border-radius: 4px; border: 1px solid var(--color-border);">
                <p style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 0.9375rem; margin: 0;" x-text="bpmAtivoObj.nome"></p>
                <label x-show="podeGerirEquipes" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                  <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens do BPM</span>
                  <input
                    type="checkbox"
                    :checked="bpmAtivoObj.isolamento_abordagens"
                    @change="alternarIsolamentoBpm(bpmAtivoObj.id, $event.target.checked)"
                  />
                </label>
              </div>
            </template>

            <!-- Sem equipe selecionada ainda (BPM sem equipes) -->
            <template x-if="equipesDoBpm(bpmAtivo).length === 0 && equipeAtiva !== 'nova-equipe'">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center; font-family: var(--font-data); font-size: 0.875rem;">
                Nenhuma equipe neste BPM. Clique em "+ Nova Equipe" para criar.
              </p>
            </template>

            <!-- Nova Equipe dentro do BPM -->
            <template x-if="equipeAtiva === 'nova-equipe'">
              <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
                <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Nova equipe</h3>
                <div style="margin-bottom: 1rem;">
                  <label class="login-field-label">Nome</label>
                  <input type="text" x-model="novaEquipe.nome" placeholder="Ex: 3ª Cia - GU 01" />
                </div>
                <button @click="criarEquipe()" :disabled="criandoEquipe || !novaEquipe.nome" class="btn btn-primary" style="width: 100%;">
                  <span x-show="!criandoEquipe">Criar equipe</span>
                  <span x-show="criandoEquipe">Criando...</span>
                </button>
              </div>
            </template>

            <!-- Equipe específica selecionada -->
            <template x-if="typeof equipeAtiva === 'number' && equipeAtivaObj">
              <div>
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-bottom: 0.75rem;">
                  <div>
                    <p style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 0.9375rem;" x-text="equipeAtivaObj.nome"></p>
                    <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="equipeAtivaObj.bpm.nome"></p>
                  </div>
                  <label x-show="podeGerirEquipes" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                    <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens da equipe</span>
                    <input
                      type="checkbox"
                      :checked="equipeAtivaObj.isolamento_abordagens"
                      @change="alternarIsolamento(equipeAtivaObj.id, $event.target.checked)"
                    />
                  </label>
                </div>
                <template x-if="usuariosDaEquipe(equipeAtiva).length === 0">
                  <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário nesta equipe.</p>
                </template>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                  <template x-for="u in usuariosDaEquipe(equipeAtiva)" :key="u.id">
                    <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '', modalMover: false }">
                      ${cardUsuario('u')}
                      <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                        <button @click="pausarUsuario(u)"
                                x-show="podePausar && u.tem_sessao"
                                style="flex: 1; font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.5rem; border-radius: 4px; background: rgba(255,165,0,0.15); color: #FFA500; border: 1px solid rgba(255,165,0,0.3); cursor: pointer;">
                          Pausar acesso
                        </button>
                        <button @click="gerarSenha(u)" x-show="podeGerarSenha" class="btn btn-secondary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                          Gerar nova senha
                        </button>
                        <button @click="modalMover = true" x-show="podeMover" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                          Mover
                        </button>
                        <button @click="excluirUsuario(u)"
                                x-show="isSuperAdmin"
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
                              <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
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
                <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
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
  const me = (typeof auth !== "undefined" && auth.getUser()) || {};
  const isSuper = !!me.is_super_admin;
  return {
    usuarios: [],
    equipes: [],
    bpms: [],
    bpmAtivo: null,
    equipeAtiva: null,
    abaAtiva: "sem-equipe",
    carregando: true,

    // Permissões do usuário logado (gating de botões). Super-admin pode tudo.
    _meGuarnicaoId: me.guarnicao_id ?? null,
    isSuperAdmin: isSuper,
    adminGlobal: isSuper || !!me.admin_global,
    podeCriar: isSuper || !!me.pode_criar_usuario,
    podeGerarSenha: isSuper || !!me.pode_gerar_senha,
    podePausar: isSuper || !!me.pode_pausar,
    podeMover: isSuper || !!me.pode_mover_equipe,
    podeGerirEquipes: isSuper || (!!me.pode_gerir_equipes && !!me.admin_global),
    mostrarFormCriacao: false,
    novaMatricula: "",
    novaEquipeId: "",
    criando: false,
    novaEquipe: { nome: "" },
    criandoEquipe: false,
    novoBpm: { nome: "" },
    criandoBpm: false,
    excluindo: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        const [usuarios, equipes, bpms] = await Promise.all([
          api.get("/admin/usuarios"),
          api.get("/admin/equipes"),
          api.get("/admin/bpms"),
        ]);
        const ordemRank = [
          "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento", "Subtenente",
          "Aspirante", "2º Tenente", "1º Tenente", "Capitão", "Major", "Tenente-Coronel", "Coronel",
        ];
        const visiveis = this.adminGlobal
          ? usuarios
          : usuarios.filter((x) => x.guarnicao_id === this._meGuarnicaoId);
        this.usuarios = visiveis.sort((a, b) => {
          const ra = ordemRank.indexOf(a.posto_graduacao ?? "");
          const rb = ordemRank.indexOf(b.posto_graduacao ?? "");
          if (rb !== ra) return rb - ra;
          return (parseInt(a.matricula) || 0) - (parseInt(b.matricula) || 0);
        });
        this.equipes = equipes;
        this.bpms = bpms;
        // Revalidar estado após reload
        if (this.bpmAtivo !== null && !this.bpms.some(b => b.id === this.bpmAtivo)) {
          this.bpmAtivo = null;
          this.equipeAtiva = null;
          this.abaAtiva = "sem-equipe";
        }
        if (typeof this.equipeAtiva === "number" && !this.equipes.some(e => e.id === this.equipeAtiva)) {
          this.equipeAtiva = null;
        }
      } catch {
        showToast("Erro ao carregar dados", "error");
      } finally {
        this.carregando = false;
      }
    },

    selecionarBpm(bpmId) {
      this.bpmAtivo = bpmId;
      this.abaAtiva = bpmId;
      // Auto-selecionar primeira equipe do BPM, se existir
      const primeiraEquipe = this.equipes.find(e => e.bpm_id === bpmId);
      this.equipeAtiva = primeiraEquipe ? primeiraEquipe.id : null;
    },

    equipesDoBpm(bpmId) {
      return this.equipes.filter(e => e.bpm_id === bpmId);
    },

    get usuariosSemEquipe() {
      return this.usuarios.filter(u => u.guarnicao_id === null || u.guarnicao_id === undefined);
    },

    usuariosDaEquipe(equipeId) {
      return this.usuarios.filter(u => u.guarnicao_id === equipeId);
    },

    usuariosDoBpm(bpmId) {
      const ids = this.equipesDoBpm(bpmId).map(e => e.id);
      return this.usuarios.filter(u => ids.includes(u.guarnicao_id));
    },

    get equipeAtivaObj() {
      if (typeof this.equipeAtiva !== "number") return null;
      return this.equipes.find(e => e.id === this.equipeAtiva) || null;
    },

    get bpmAtivoObj() {
      return this.bpms.find(b => b.id === this.bpmAtivo) || null;
    },

    abrirCriarUsuario() {
      this.novaMatricula = "";
      this.novaEquipeId = typeof this.equipeAtiva === "number" ? String(this.equipeAtiva) : "";
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
      if (!this.novaEquipe.nome.trim() || this.bpmAtivo === null) return;
      this.criandoEquipe = true;
      try {
        const equipe = await api.post("/admin/equipes", {
          nome: this.novaEquipe.nome.trim(),
          bpm_id: this.bpmAtivo,
        });
        this.novaEquipe = { nome: "" };
        await this.carregar();
        this.equipeAtiva = equipe.id;
      } catch (e) {
        showToast(e.message || "Erro ao criar equipe", "error");
      } finally {
        this.criandoEquipe = false;
      }
    },

    async criarBpm() {
      if (!this.novoBpm.nome.trim()) return;
      this.criandoBpm = true;
      try {
        const bpm = await api.post("/admin/bpms", { nome: this.novoBpm.nome.trim() });
        this.novoBpm = { nome: "" };
        await this.carregar();
        this.selecionarBpm(bpm.id);
      } catch (e) {
        showToast(e.message || "Erro ao criar BPM", "error");
      } finally {
        this.criandoBpm = false;
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

    async alternarIsolamentoBpm(bpmId, valor) {
      try {
        await api.patch(`/admin/bpms/${bpmId}/toggle-isolamento`, {
          isolamento_abordagens: valor,
        });
        showToast(valor ? "Isolamento de BPM ativado" : "Isolamento de BPM desativado", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao atualizar BPM", "error");
        await this.carregar();
      }
    },
  };
}
