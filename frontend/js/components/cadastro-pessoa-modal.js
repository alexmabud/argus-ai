/**
 * Modal reutilizável para cadastro de nova pessoa (sem abordagem associada).
 *
 * Usado pela Consulta IA (busca sem resultado) e pelo botão "Cadastrar Nova
 * Pessoa" da home. Aberto via abrirCadastroPessoa(prefillTexto,
 * mostrarAvisoAbordagem), fechado e resetado via fecharCadastroPessoa(). Se
 * o host expõe um método viewPessoa(id) (caso da Consulta IA, que preserva
 * estado de busca ao voltar), ele é usado para navegar até a ficha após
 * salvar; senão, navega direto para a ficha da pessoa criada.
 *
 * Quando aberto com mostrarAvisoAbordagem=true (caso do botão da home),
 * exibe um aviso no topo do modal esclarecendo que o formulário é só para
 * cadastro de pessoa, com link para Nova Abordagem — a Consulta IA abre sem
 * esse aviso (contexto onde a confusão é menos provável).
 *
 * Uso nas páginas:
 *   x-data: "{ ...minhaPage(), ...cadastroPessoaModal() }"
 *   Incluir no template: ${cadastroPessoaModalHTML()}
 *   Acionar: abrirCadastroPessoa() ou abrirCadastroPessoa('texto buscado')
 *   Acionar com aviso: abrirCadastroPessoa(null, true)
 */

/**
 * Retorna o HTML do modal para ser incluído nos templates das páginas.
 * @returns {string} HTML do modal
 */
function cadastroPessoaModalHTML() {
  return `
    <template x-teleport="body">
    <div x-show="showCadastroPessoa" x-cloak
         @click.self="fecharCadastroPessoa()"
         style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 200; overflow: hidden; display: flex; align-items: flex-start; justify-content: center; padding: 1rem;">
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 16px; width: 100%; max-width: min(92vw, 480px); box-sizing: border-box; max-height: calc(100vh - 2rem); overflow-y: auto; display:flex; flex-direction:column; gap:12px;">

        <div x-show="cpMostrarAvisoAbordagem" x-cloak
             style="background: rgba(255,59,59,0.1); border: 1px solid rgba(255,59,59,0.4); border-radius: 4px; padding: 10px 12px;">
          <p style="font-family:var(--font-data);font-size:10px;font-weight:700;color:var(--color-danger);text-transform:uppercase;letter-spacing:0.08em;margin:0 0 4px 0;">Atenção</p>
          <p style="font-family:var(--font-body);font-size:13px;color:var(--color-text);margin:0;line-height:1.4;">
            Este formulário cadastra uma <strong>pessoa</strong>, sem registrar nenhuma abordagem. Se você quer registrar uma abordagem, use o botão
            <span @click="irParaNovaAbordagem()" style="color:var(--color-primary);font-weight:600;text-decoration:underline;cursor:pointer;">Nova Abordagem</span>.
          </p>
        </div>

        <div style="display:flex;align-items:center;justify-content:space-between;">
          <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text);text-transform:uppercase;letter-spacing:0.06em;">Cadastrar Pessoa</h3>
          <button @click="fecharCadastroPessoa()"
                  style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);background:transparent;border:none;cursor:pointer;">Cancelar</button>
        </div>

        <div>
          <label class="login-field-label">Nome *</label>
          <input type="text" :value="novaPessoa.nome"
                 @input="novaPessoa.nome = $event.target.value; cpOnInputNome()"
                 placeholder="Nome completo">
        </div>

        <div x-show="cpDuplicatas.length > 0" x-cloak style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:#FFD700;text-transform:uppercase;letter-spacing:0.08em;">
            Possível pessoa já cadastrada
          </p>
          <template x-for="p in cpDuplicatas" :key="'dup-' + p.id">
            <div @click="cpVerFicha(p.id)"
                 class="hov-list-card"
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url" :alt="'Foto de ' + p.nome"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width:32px;height:32px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">
                  <svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <div style="flex:1;min-width:0;">
                <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);" x-text="p.nome"></p>
                <p x-show="p.cpf_masked" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'CPF: ' + p.cpf_masked"></p>
                <p x-show="p.apelido" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Vulgo: ' + p.apelido"></p>
                <p x-show="p.data_nascimento" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Nasc.: ' + p.data_nascimento"></p>
              </div>
            </div>
          </template>
        </div>

        <div>
          <label class="login-field-label">CPF</label>
          <input type="text" :value="novaPessoa.cpf"
                 @input="novaPessoa.cpf = formatarCPF($event.target.value); cpfCadastroErro = novaPessoa.cpf.length === 14 && !validarCPF(novaPessoa.cpf) ? 'CPF inválido' : ''; cpOnInputCPF()"
                 placeholder="000.000.000-00" maxlength="14" inputmode="numeric">
          <p x-show="cpfCadastroErro" x-text="cpfCadastroErro"
             style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);margin-top:4px;"></p>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
          <div>
            <label class="login-field-label">Data de Nascimento</label>
            <input type="text" x-model="novaPessoa.data_nascimento"
                   @input="novaPessoa.data_nascimento = formatarData($event.target.value)"
                   placeholder="DD/MM/AAAA" maxlength="10">
          </div>
          <div>
            <label class="login-field-label">Vulgo</label>
            <input type="text" x-model="novaPessoa.apelido" placeholder="Apelido">
          </div>
        </div>

        <div>
          <label class="login-field-label">Nome da mãe</label>
          <input type="text" x-model="novaPessoa.nome_mae" placeholder="Nome completo da mãe" maxlength="300">
        </div>

        <div>
          <label class="login-field-label">Endereço</label>
          <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e número">
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
          <div>
            <label class="login-field-label">Estado (UF)</label>
            <select x-model="cpEstadoId"
                    @change="cpCidadeId=null;cpCidadeTexto='';cpBairroId=null;cpBairroTexto='';cpCidadeSugestoes=[];cpBairroSugestoes=[];cpBuscarCidades()"
                    style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px 14px;font-size:13px;color:var(--color-text);font-family:var(--font-body);box-sizing:border-box;">
              <option value="">Selecione...</option>
              <template x-for="est in cpEstados" :key="est.id">
                <option :value="est.id" x-text="est.sigla + ' — ' + est.nome_exibicao"></option>
              </template>
            </select>
          </div>
          <div style="position:relative;">
            <label class="login-field-label">Cidade</label>
            <input type="text" x-model="cpCidadeTexto" :disabled="!cpEstadoId"
                   @focus="cpBuscarCidades()"
                   @input.debounce.300ms="cpBuscarCidades()"
                   @blur.debounce.200ms="cpCidadeSugestoes=[]"
                   placeholder="Cidade">
            <div x-show="cpCidadeSugestoes.length > 0 || cpCidadeCadastrarNovo"
                 style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
              <template x-for="cidade in cpCidadeSugestoes" :key="cidade.id">
                <div @mousedown.prevent="cpSelecionarCidade(cidade)"
                     class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                  <span x-text="cidade.nome_exibicao"></span>
                </div>
              </template>
              <div x-show="cpCidadeCadastrarNovo" @mousedown.prevent="cpCadastrarCidade()"
                   class="hov-row-surface"
                   style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-primary);border-top:1px solid var(--color-border);">
                + Cadastrar "<span x-text="cpCidadeTexto"></span>"
              </div>
            </div>
          </div>
          <div style="position:relative;">
            <label class="login-field-label">Bairro</label>
            <input type="text" x-model="cpBairroTexto" :disabled="!cpCidadeId"
                   @focus="cpBuscarBairros()"
                   @input.debounce.300ms="cpBuscarBairros()"
                   @blur.debounce.200ms="cpBairroSugestoes=[]"
                   placeholder="Bairro">
            <div x-show="cpBairroSugestoes.length > 0 || cpBairroCadastrarNovo"
                 style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
              <template x-for="bairro in cpBairroSugestoes" :key="bairro.id">
                <div @mousedown.prevent="cpSelecionarBairro(bairro)"
                     class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                  <span x-text="bairro.nome_exibicao"></span>
                </div>
              </template>
              <div x-show="cpBairroCadastrarNovo" @mousedown.prevent="cpCadastrarBairro()"
                   class="hov-row-surface"
                   style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-primary);border-top:1px solid var(--color-border);">
                + Cadastrar "<span x-text="cpBairroTexto"></span>"
              </div>
            </div>
          </div>
        </div>

        <div>
          <label class="login-field-label">Foto</label>
          <label style="cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:var(--font-data);font-size:11px;padding:6px 12px;border-radius:4px;background:var(--color-surface-hover);color:var(--color-primary);border:1px solid var(--color-border);transition:all 150ms;">
            Selecionar foto
            <input type="file" accept="image/*"
                   @change="if (fotoPessoaPreviewUrl) URL.revokeObjectURL(fotoPessoaPreviewUrl); fotoPessoa = $event.target.files[0] || null; fotoPessoaPreviewUrl = fotoPessoa ? URL.createObjectURL(fotoPessoa) : ''"
                   class="hidden">
          </label>
          <template x-if="fotoPessoa">
            <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
              <img :src="fotoPessoaPreviewUrl" style="width:48px;height:48px;border-radius:4px;object-fit:cover;flex-shrink:0;">
              <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="fotoPessoa?.name"></span>
            </div>
          </template>
        </div>

        <button @click="criarPessoa()" class="btn btn-primary"
                :disabled="salvandoPessoa || !novaPessoa.nome.trim() || !!cpfCadastroErro">
          <span x-show="!salvandoPessoa">SALVAR PESSOA</span>
          <span x-show="salvandoPessoa" style="display:flex;align-items:center;justify-content:center;gap:8px;">
            <span class="spinner"></span> SALVANDO...
          </span>
        </button>
        <p x-show="erroCadastro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="erroCadastro"></p>
      </div>
    </div>
    </template>
  `;
}

/**
 * Componente Alpine.js do modal de cadastro de pessoa.
 *
 * Mantém estado do formulário (dados pessoais, endereço em cascata
 * estado/cidade/bairro com autocomplete, foto) e a chamada de criação.
 */
function cadastroPessoaModal() {
  return {
    showCadastroPessoa: false,
    cpMostrarAvisoAbordagem: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", nome_mae: "", endereco: "" },
    fotoPessoa: null,
    fotoPessoaPreviewUrl: "",
    salvandoPessoa: false,
    erroCadastro: null,
    cpfCadastroErro: "",
    // Localidade cascata (cadastro pessoa)
    cpEstadoId: null,
    cpCidadeId: null,
    cpCidadeTexto: "",
    cpBairroId: null,
    cpBairroTexto: "",
    cpEstados: [],
    cpCidadeSugestoes: [],
    cpBairroSugestoes: [],
    cpCidadeCadastrarNovo: false,
    cpBairroCadastrarNovo: false,
    cpDuplicatas: [],
    _cpTimerNome: null,

    /**
     * Abre o modal automaticamente ao chegar na home, quando sinalizado por
     * outra página (ex.: link "Cadastrar Nova Pessoa" em Nova Abordagem) via
     * a flag global window.__argusAbrirCadastroPessoaHome. Chamado por
     * x-init no wrapper do botão da home — não é usado pela Consulta IA,
     * que já tem seu próprio init() nesse mesmo x-data mesclado.
     */
    initCadastroPessoaModal() {
      if (window.__argusAbrirCadastroPessoaHome) {
        window.__argusAbrirCadastroPessoaHome = false;
        this.abrirCadastroPessoa(null, true);
      }
    },

    /**
     * Abre o modal, carrega estados e opcionalmente pré-preenche nome ou CPF
     * a partir de um texto já digitado (ex.: busca sem resultado).
     * @param {string} [prefillTexto] - Nome ou CPF já digitado alhures.
     * @param {boolean} [mostrarAvisoAbordagem] - Exibe o aviso de que este
     *   formulário é só para cadastro de pessoa (usado pelo botão da home,
     *   onde a confusão com "Nova Abordagem" é mais provável).
     */
    abrirCadastroPessoa(prefillTexto, mostrarAvisoAbordagem = false) {
      this.showCadastroPessoa = true;
      this.cpMostrarAvisoAbordagem = mostrarAvisoAbordagem;
      this.cpCarregarEstados();
      if (prefillTexto) {
        if (/^\d/.test(prefillTexto)) {
          this.novaPessoa.cpf = prefillTexto;
        } else {
          this.novaPessoa.nome = prefillTexto;
        }
      }
    },

    /**
     * Fecha o modal e reseta todos os campos do formulário.
     */
    fecharCadastroPessoa() {
      this.showCadastroPessoa = false;
      this.cpMostrarAvisoAbordagem = false;
      this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", nome_mae: "", endereco: "" };
      this.cpEstadoId = null;
      this.cpCidadeId = null;
      this.cpCidadeTexto = "";
      this.cpBairroId = null;
      this.cpBairroTexto = "";
      this.cpCidadeSugestoes = [];
      this.cpBairroSugestoes = [];
      this.cpCidadeCadastrarNovo = false;
      this.cpBairroCadastrarNovo = false;
      this.fotoPessoa = null;
      this.fotoPessoaPreviewUrl = "";
      this.erroCadastro = null;
      this.cpfCadastroErro = "";
      this.cpDuplicatas = [];
      clearTimeout(this._cpTimerNome);
    },

    /**
     * Fecha o modal no "voltar" quando este componente está sozinho no
     * escopo (caso da home). Na Consulta IA, quem trata o voltar é o
     * interceptBack() de consultaPage() — que também fecha este modal e
     * precisa vir depois deste no merge do x-data para não ser sobrescrito.
     */
    interceptBack() {
      if (this.showCadastroPessoa) {
        this.fecharCadastroPessoa();
        return true;
      }
      return false;
    },

    /**
     * Fecha o modal e navega para Nova Abordagem (link do aviso).
     */
    irParaNovaAbordagem() {
      this.fecharCadastroPessoa();
      window.dispatchEvent(new CustomEvent("navigate", { detail: "abordagem-nova" }));
    },

    /**
     * Dispara a checagem de duplicidade por nome com debounce, exigindo ao
     * menos 3 caracteres para evitar buscas ruidosas com o campo quase vazio.
     */
    cpOnInputNome() {
      clearTimeout(this._cpTimerNome);
      const nome = this.novaPessoa.nome.trim();
      if (nome.length < 3) {
        this.cpDuplicatas = [];
        return;
      }
      this._cpTimerNome = setTimeout(() => this.cpBuscarDuplicatas(nome), 400);
    },

    /**
     * Busca pessoas já cadastradas com nome parecido, reaproveitando o
     * endpoint unificado de consulta (fuzzy pg_trgm no backend).
     * @param {string} query - Nome (ou trecho) digitado no formulário.
     */
    async cpBuscarDuplicatas(query) {
      try {
        const r = await api.get(`/consultas/?q=${encodeURIComponent(query)}&tipo=pessoa&limit=5`);
        this.cpDuplicatas = r.pessoas || [];
      } catch (e) {
        console.error(e);
      }
    },

    /**
     * Dispara a checagem de duplicidade por CPF assim que o campo fica
     * completo (11 dígitos) — sem debounce, já que a busca por hash exige o
     * valor exato e só faz sentido rodar uma vez o CPF esteja inteiro.
     * CPF incompleto limpa o painel (evita card de uma busca antiga).
     */
    cpOnInputCPF() {
      const digits = this.novaPessoa.cpf.replace(/\D/g, "");
      if (digits.length !== 11) {
        this.cpDuplicatas = [];
        return;
      }
      this.cpBuscarDuplicatas(this.novaPessoa.cpf);
    },

    /**
     * Fecha o modal e navega para a ficha completa de uma pessoa apontada
     * como possível duplicata, sem criar cadastro novo.
     * @param {number} id - Id da pessoa já cadastrada.
     */
    cpVerFicha(id) {
      this.fecharCadastroPessoa();
      this.cpNavegarParaFicha(id);
    },

    /**
     * Navega até a ficha de uma pessoa via viewPessoa do host (quando
     * existir — preserva estado de busca da Consulta IA) ou, senão, navega
     * diretamente. Compartilhado entre criarPessoa() (após salvar) e
     * cpVerFicha() (ao apontar uma duplicata já cadastrada).
     * @param {number} id - Id da pessoa a exibir.
     */
    cpNavegarParaFicha(id) {
      if (typeof this.viewPessoa === "function") {
        this.viewPessoa(id);
      } else {
        const appEl = document.querySelector("[x-data]");
        if (appEl?._x_dataStack) {
          appEl._x_dataStack[0]._pessoaId = id;
          appEl._x_dataStack[0].navigate("pessoa-detalhe");
        }
      }
    },

    async cpCarregarEstados() {
      if (this.cpEstados.length > 0) return;
      try { this.cpEstados = await api.get('/localidades?tipo=estado'); } catch (e) { console.error(e); }
    },

    async cpBuscarCidades() {
      const q = this.cpCidadeTexto.trim();
      if (!this.cpEstadoId) { this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false; return; }
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}`;
        const r = await api.get(url);
        this.cpCidadeSugestoes = r;
        this.cpCidadeCadastrarNovo = q.length >= 1 && r.length === 0;
      } catch (e) { console.error(e); }
    },

    async cpBuscarBairros() {
      const q = this.cpBairroTexto.trim();
      if (!this.cpCidadeId) { this.cpBairroSugestoes = []; this.cpBairroCadastrarNovo = false; return; }
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}`;
        const r = await api.get(url);
        this.cpBairroSugestoes = r;
        this.cpBairroCadastrarNovo = q.length >= 1 && r.length === 0;
      } catch (e) { console.error(e); }
    },

    cpSelecionarCidade(cidade) {
      this.cpCidadeId = cidade.id; this.cpCidadeTexto = cidade.nome_exibicao;
      this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false;
      this.cpBairroId = null; this.cpBairroTexto = '';
      this.cpBuscarBairros();
    },

    cpSelecionarBairro(bairro) {
      this.cpBairroId = bairro.id; this.cpBairroTexto = bairro.nome_exibicao;
      this.cpBairroSugestoes = []; this.cpBairroCadastrarNovo = false;
    },

    async cpCadastrarCidade() {
      const nome = this.cpCidadeTexto.trim();
      if (!nome || !this.cpEstadoId) return;
      try { this.cpSelecionarCidade(await api.post('/localidades', { nome, tipo: 'cidade', parent_id: parseInt(this.cpEstadoId) })); }
      catch (e) { showToast('Erro ao cadastrar cidade', 'error'); }
    },

    async cpCadastrarBairro() {
      const nome = this.cpBairroTexto.trim();
      if (!nome || !this.cpCidadeId) return;
      try { this.cpSelecionarBairro(await api.post('/localidades', { nome, tipo: 'bairro', parent_id: this.cpCidadeId })); }
      catch (e) { showToast('Erro ao cadastrar bairro', 'error'); }
    },

    /**
     * Cria a pessoa e, se houver, endereço e foto associados. Ao final,
     * navega para a ficha via viewPessoa do host (quando existir — preserva
     * estado de busca da Consulta IA) ou, senão, navega diretamente.
     */
    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroCadastro = "Nome é obrigatório.";
        return;
      }

      if (this.novaPessoa.cpf.trim() && !validarCPF(this.novaPessoa.cpf)) {
        this.cpfCadastroErro = "CPF inválido";
        return;
      }

      this.salvandoPessoa = true;
      this.erroCadastro = null;

      try {
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) pessoaData.cpf = this.novaPessoa.cpf.trim();
        const dataNasc = parseDateBR(this.novaPessoa.data_nascimento);
        if (dataNasc) pessoaData.data_nascimento = dataNasc;
        if (this.novaPessoa.apelido.trim()) pessoaData.apelido = this.novaPessoa.apelido.trim();
        if (this.novaPessoa.nome_mae.trim()) pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();

        const pessoa = await api.post("/pessoas/", pessoaData);

        const temEndereco = this.novaPessoa.endereco.trim() || this.cpEstadoId || this.cpCidadeId;

        // Endereço e foto são independentes entre si (só dependem de pessoa.id) — rodam em paralelo.
        const tarefas = [];
        if (temEndereco) {
          tarefas.push(api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            estado_id: this.cpEstadoId ? parseInt(this.cpEstadoId) : null,
            cidade_id: this.cpCidadeId || null,
            bairro_id: this.cpBairroId || null,
          }));
        }
        if (this.fotoPessoa) {
          tarefas.push(api.uploadFile("/fotos/upload", this.fotoPessoa, {
            tipo: "rosto",
            pessoa_id: pessoa.id,
          }));
        }
        if (tarefas.length > 0) {
          await Promise.all(tarefas);
        }

        this.fecharCadastroPessoa();
        showToast("Pessoa cadastrada com sucesso!", "success");
        this.cpNavegarParaFicha(pessoa.id);
      } catch (err) {
        this.erroCadastro = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },
  };
}
