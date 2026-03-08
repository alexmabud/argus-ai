/**
 * Página de nova abordagem — Argus AI.
 *
 * Formulário completo para registro de abordagem com busca/cadastro
 * de pessoas como primeiro passo, GPS automático, autocomplete de
 * veículos, captura de foto, entrada por voz e envio offline.
 */
function renderAbordagemNova() {
  return `
    <div x-data="abordagemForm()" x-init="initForm()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Nova Abordagem</h2>

      <!-- 1. Pessoas abordadas (primeiro campo) -->
      <div class="card space-y-3">
        <label class="text-sm font-medium text-slate-300 block">Pessoas abordadas</label>

        <div x-data="autocompleteComponent('pessoa')" class="relative">
          <input type="text" x-model="query" @input="onInput()" @focus="showDropdown = results.length > 0 || noResults"
                 placeholder="Buscar por nome ou CPF..." class="w-full">

          <!-- Dropdown resultados -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               class="absolute z-20 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg max-h-56 overflow-y-auto shadow-lg">

            <!-- Resultados encontrados -->
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('pessoa-selected', { selected: selected })"
                      class="w-full text-left px-3 py-2 hover:bg-slate-700 text-sm text-slate-200 border-b border-slate-700 last:border-0">
                <span x-text="getLabel(item)"></span>
                <span x-show="item.cpf_masked" class="text-xs text-slate-400 ml-2" x-text="item.cpf_masked"></span>
              </button>
            </template>

            <!-- Nenhum resultado -->
            <div x-show="noResults" class="px-3 py-3 text-sm text-slate-400">
              <p>Nenhuma pessoa encontrada.</p>
              <button @click="showDropdown = false; $dispatch('abrir-cadastro-pessoa', { query: query })"
                      class="mt-2 w-full text-left text-blue-400 hover:text-blue-300 font-medium">
                + Cadastrar novo abordado
              </button>
            </div>
          </div>

          <!-- Tags selecionados -->
          <div class="flex flex-wrap gap-2 mt-2">
            <template x-for="item in selected" :key="item.id">
              <span class="bg-blue-900/50 text-blue-300 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('pessoa-selected', { selected: selected })"
                        class="text-blue-400 hover:text-white">&times;</button>
              </span>
            </template>
          </div>
        </div>

        <!-- Botão para cadastrar sem buscar -->
        <button x-show="!showNovaPessoa" @click="showNovaPessoa = true"
                class="text-xs text-blue-400 hover:text-blue-300">
          + Adicionar pessoa não cadastrada
        </button>

        <!-- Formulário inline: cadastrar nova pessoa -->
        <div x-show="showNovaPessoa" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-slate-200">Cadastrar novo abordado</h3>
            <button @click="showNovaPessoa = false; novaPessoa = {nome:'',cpf:'',data_nascimento:'',apelido:'',endereco:'',bairro:'',cidade:'',estado:''}"
                    class="text-slate-400 hover:text-white text-xs">Cancelar</button>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo" class="w-full">
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">CPF</label>
            <input type="text" :value="novaPessoa.cpf" @input="novaPessoa.cpf = formatarCPF($event.target.value)" placeholder="000.000.000-00" maxlength="14" inputmode="numeric" class="w-full">
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Data de nascimento</label>
              <input type="date" x-model="novaPessoa.data_nascimento" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Vulgo</label>
              <input type="text" x-model="novaPessoa.apelido" placeholder="Apelido" class="w-full">
            </div>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Endereço</label>
            <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e número" class="w-full">
          </div>

          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Bairro</label>
              <input type="text" list="lista-bairros-pessoa" x-model="novaPessoa.bairro" placeholder="Bairro" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Cidade</label>
              <input type="text" list="lista-cidades-pessoa" x-model="novaPessoa.cidade" placeholder="Cidade" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
              <input type="text" list="lista-estados-pessoa" x-model="novaPessoa.estado" placeholder="DF" maxlength="2" class="w-full uppercase">
            </div>
          </div>

          <!-- Datalists para autocomplete de localização -->
          <datalist id="lista-bairros-pessoa">
            <template x-for="b in localidades.bairros" :key="b"><option :value="b"></option></template>
          </datalist>
          <datalist id="lista-cidades-pessoa">
            <template x-for="c in localidades.cidades" :key="c"><option :value="c"></option></template>
          </datalist>
          <datalist id="lista-estados-pessoa">
            <template x-for="e in localidades.estados" :key="e"><option :value="e"></option></template>
          </datalist>

          <button @click="criarPessoa()" class="btn btn-primary text-sm" :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
            <span x-show="!salvandoPessoa">Salvar e adicionar</span>
            <span x-show="salvandoPessoa" class="flex items-center gap-2">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroPessoa" class="text-xs text-red-400" x-text="erroPessoa"></p>
        </div>

        <!-- Info e ações por abordado selecionado -->
        <div x-show="pessoasSelecionadas.length > 0" class="border-t border-slate-700 pt-3 space-y-3">
          <template x-for="p in pessoasSelecionadas" :key="p.id">
            <div class="bg-slate-800/30 rounded-lg p-3 space-y-2">
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm text-slate-300 flex-1 truncate" x-text="p.nome"></span>
                <label :for="'foto-p-' + p.id"
                       class="cursor-pointer text-xs px-2 py-1 rounded flex items-center gap-1"
                       :class="fotosPessoas[p.id] ? 'bg-green-900/50 text-green-400' : 'bg-slate-700 text-blue-400 hover:bg-slate-600'">
                  <span x-text="fotosPessoas[p.id] ? '✓ Foto' : '📷 Foto'"></span>
                </label>
                <input type="file" accept="image/*" capture="environment"
                       :id="'foto-p-' + p.id" class="hidden"
                       @change="fotosPessoas = {...fotosPessoas, [p.id]: $event.target.files[0]}">
              </div>

              <!-- Endereço atual (se houver) -->
              <div x-show="pessoaEnderecos[p.id]?.length > 0" class="text-xs text-slate-400">
                <span class="text-slate-500">Endereço atual:</span>
                <span x-text="formatEndereco(pessoaEnderecos[p.id]?.[0])"></span>
              </div>

              <!-- Botão novo endereço -->
              <button x-show="!novoEnderecoAberto[p.id]" @click="novoEnderecoAberto = {...novoEnderecoAberto, [p.id]: true}"
                      class="text-xs text-blue-400 hover:text-blue-300">
                + Cadastrar novo endereço
              </button>

              <!-- Mini-form novo endereço -->
              <div x-show="novoEnderecoAberto[p.id]" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-300">Novo endereço</span>
                  <button @click="novoEnderecoAberto = {...novoEnderecoAberto, [p.id]: false}"
                          class="text-slate-400 hover:text-white text-xs">Cancelar</button>
                </div>
                <input type="text" x-model="novoEnderecoData[p.id + '_endereco']" placeholder="Rua e número" class="w-full text-sm">
                <div class="grid grid-cols-3 gap-2">
                  <input type="text" list="lista-bairros-pessoa" x-model="novoEnderecoData[p.id + '_bairro']" placeholder="Bairro" class="w-full text-sm">
                  <input type="text" list="lista-cidades-pessoa" x-model="novoEnderecoData[p.id + '_cidade']" placeholder="Cidade" class="w-full text-sm">
                  <input type="text" list="lista-estados-pessoa" x-model="novoEnderecoData[p.id + '_estado']" placeholder="UF" maxlength="2" class="w-full text-sm uppercase">
                </div>
                <button @click="salvarNovoEndereco(p.id)" class="btn btn-primary text-xs py-1"
                        :disabled="salvandoEndereco[p.id] || !novoEnderecoData[p.id + '_endereco']?.trim()">
                  <span x-show="!salvandoEndereco[p.id]">Salvar endereço</span>
                  <span x-show="salvandoEndereco[p.id]" class="flex items-center gap-1">
                    <span class="spinner"></span> Salvando...
                  </span>
                </button>
                <p x-show="erroEndereco[p.id]" class="text-xs text-red-400" x-text="erroEndereco[p.id]"></p>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 3. Localização da abordagem -->
      <div class="card space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-slate-300">Localização da abordagem</span>
          <button @click="captureGPS()" class="text-xs text-blue-400 hover:text-blue-300" :disabled="gpsLoading">
            <span x-show="!gpsLoading">Atualizar GPS</span>
            <span x-show="gpsLoading">Obtendo...</span>
          </button>
        </div>
        <p x-show="endereco" class="text-sm text-slate-400" x-text="endereco"></p>
        <p x-show="!endereco && !gpsLoading" class="text-sm text-slate-500">GPS não capturado</p>
        <p x-show="latitude" class="text-xs text-slate-500" x-text="latitude?.toFixed(6) + ', ' + longitude?.toFixed(6)"></p>
      </div>

      <!-- 4. Veículo envolvido na abordagem -->
      <div class="card space-y-3">
        <label class="text-sm font-medium text-slate-300 block">Veículo envolvido na abordagem</label>

        <div x-data="autocompleteComponent('veiculo')" class="relative">
          <input type="text" :value="query" @input="query = formatarPlaca($event.target.value); onInput()"
                 @focus="showDropdown = results.length > 0 || noResults"
                 placeholder="Buscar por placa..." maxlength="8"
                 class="w-full">

          <!-- Dropdown resultados -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               class="absolute z-20 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg max-h-56 overflow-y-auto shadow-lg">

            <!-- Resultados encontrados -->
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('veiculo-selected', { selected: selected })"
                      class="w-full text-left px-3 py-2 hover:bg-slate-700 text-sm text-slate-200 border-b border-slate-700 last:border-0"
                      x-text="getLabel(item)">
              </button>
            </template>

            <!-- Nenhum resultado -->
            <div x-show="noResults" class="px-3 py-3 text-sm text-slate-400">
              <p>Nenhum veículo encontrado.</p>
              <button @click="showDropdown = false; $dispatch('abrir-cadastro-veiculo', { query: query })"
                      class="mt-2 w-full text-left text-blue-400 hover:text-blue-300 font-medium">
                + Cadastrar novo veículo
              </button>
            </div>
          </div>

          <!-- Tags selecionados -->
          <div class="flex flex-wrap gap-2 mt-2">
            <template x-for="item in selected" :key="item.id">
              <span class="bg-green-900/50 text-green-300 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('veiculo-selected', { selected: selected })"
                        class="text-green-400 hover:text-white">&times;</button>
              </span>
            </template>
          </div>
        </div>

        <!-- Vínculo veículo → abordado -->
        <div x-show="veiculosSelecionados.length > 0 && pessoasSelecionadas.length > 0" class="pt-1 space-y-2">
          <p class="text-xs text-slate-400">Vincular veículo ao abordado:</p>
          <template x-for="v in veiculosSelecionados" :key="v.id">
            <div class="space-y-1">
              <span class="text-xs font-semibold text-green-400" x-text="v.placa + (v.modelo ? ' — ' + v.modelo : '')"></span>
              <div class="flex flex-wrap gap-2 mt-1">
                <template x-for="p in pessoasSelecionadas" :key="p.id">
                  <button type="button"
                          @click="veiculoPorPessoa = {...veiculoPorPessoa, [v.id]: veiculoPorPessoa[v.id] === p.id ? null : p.id}"
                          class="text-xs px-2 py-1 rounded-full border transition-colors"
                          :class="veiculoPorPessoa[v.id] === p.id
                            ? 'bg-blue-600 border-blue-500 text-white'
                            : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'">
                    <span x-text="p.nome.split(' ')[0]"></span>
                  </button>
                </template>
              </div>
            </div>
          </template>
        </div>

        <!-- Botão para cadastrar sem buscar -->
        <button x-show="!showNovoVeiculo" @click="showNovoVeiculo = true"
                class="text-xs text-blue-400 hover:text-blue-300">
          + Adicionar veículo não cadastrado
        </button>

        <!-- Formulário inline: cadastrar novo veículo -->
        <div x-show="showNovoVeiculo" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-slate-200">Cadastrar novo veículo</h3>
            <button @click="showNovoVeiculo = false; novoVeiculo = {placa:'',modelo:'',cor:'',ano:''}"
                    class="text-slate-400 hover:text-white text-xs">Cancelar</button>
          </div>

          <!-- Placa + Foto -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Placa *</label>
              <input type="text" :value="novoVeiculo.placa"
                     @input="novoVeiculo.placa = formatarPlaca($event.target.value)"
                     placeholder="ABC-1234" maxlength="8" class="w-full uppercase">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Foto do veículo</label>
              <input type="file" accept="image/*" capture="environment"
                     @change="onFotoVeiculoSelected($event)"
                     class="text-sm text-slate-400 w-full">
              <p x-show="fotoVeiculoFile" class="text-xs text-slate-500 mt-1" x-text="fotoVeiculoFile?.name"></p>
            </div>
          </div>

          <!-- Modelo + Cor + Ano -->
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Modelo</label>
              <input type="text" list="lista-modelos-veiculo" x-model="novoVeiculo.modelo" placeholder="Ex: Gol" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Cor</label>
              <input type="text" list="lista-cores-veiculo" x-model="novoVeiculo.cor" placeholder="Ex: Branco" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Ano</label>
              <input type="number" x-model="novoVeiculo.ano" placeholder="2020" min="1900" max="2100" class="w-full">
            </div>
          </div>

          <!-- Datalists para autocomplete de veículo -->
          <datalist id="lista-modelos-veiculo">
            <template x-for="m in veiculoLocalidades.modelos" :key="m"><option :value="m"></option></template>
          </datalist>
          <datalist id="lista-cores-veiculo">
            <template x-for="c in veiculoLocalidades.cores" :key="c"><option :value="c"></option></template>
          </datalist>

          <button @click="criarVeiculo()" class="btn btn-primary text-sm" :disabled="salvandoVeiculo || !novoVeiculo.placa.trim()">
            <span x-show="!salvandoVeiculo">Salvar e adicionar</span>
            <span x-show="salvandoVeiculo" class="flex items-center gap-2">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroVeiculo" class="text-xs text-red-400" x-text="erroVeiculo"></p>
        </div>
      </div>

      <!-- 5. Observação -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-sm text-slate-300">Observação</label>
          <button x-show="voiceSupported" @click="toggleVoice()"
                  class="text-xs px-2 py-1 rounded"
                  :class="recording ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300'">
            <span x-text="recording ? 'Parar' : 'Voz'"></span>
          </button>
        </div>
        <textarea x-model="observacao" rows="3" placeholder="Descreva a abordagem..."></textarea>
      </div>

      <!-- 6. Submit -->
      <div class="space-y-3 pt-2">
        <button @click="submit()" class="btn btn-primary" :disabled="submitting">
          <span x-show="!submitting">Registrar Abordagem</span>
          <span x-show="submitting" class="flex items-center gap-2">
            <span class="spinner"></span> Salvando...
          </span>
        </button>

        <p x-show="erro" class="text-sm text-red-400" x-text="erro"></p>
        <p x-show="sucesso" class="text-sm text-green-400" x-text="sucesso"></p>
      </div>
    </div>
  `;
}

function abordagemForm() {
  return {
    // GPS
    latitude: null,
    longitude: null,
    endereco: "",
    gpsLoading: false,

    // Formulário
    observacao: "",
    pessoaIds: [],
    pessoasSelecionadas: [],
    fotosPessoas: {},
    veiculoIds: [],
    veiculosSelecionados: [],
    veiculoPorPessoa: {},
    fotoVeiculoFile: null,
    submitting: false,
    clientId: null,
    erro: null,
    sucesso: null,

    // Voz
    recording: false,
    voiceSupported: typeof webkitSpeechRecognition !== "undefined" || typeof SpeechRecognition !== "undefined",

    // Cadastro nova pessoa
    showNovaPessoa: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" },
    salvandoPessoa: false,
    erroPessoa: null,

    // Cadastro novo veículo
    showNovoVeiculo: false,
    novoVeiculo: { placa: "", modelo: "", cor: "", ano: "" },
    salvandoVeiculo: false,
    erroVeiculo: null,

    // Endereço de pessoa existente
    pessoaEnderecos: {},
    novoEnderecoAberto: {},
    novoEnderecoData: {},
    salvandoEndereco: {},
    erroEndereco: {},

    // Autocomplete de localidades (endereço pessoa)
    localidades: { bairros: [], cidades: [], estados: [] },

    // Autocomplete de localidades (veículo)
    veiculoLocalidades: { modelos: [], cores: [] },

    async initForm() {
      // Capturar GPS automaticamente
      this.captureGPS();

      // Carregar localidades para autocomplete
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch { /* silencioso — datalists ficam vazios */ }
      try {
        this.veiculoLocalidades = await api.get("/veiculos/localidades");
      } catch { /* silencioso */ }

      // Escutar seleções de autocomplete
      this.$el.addEventListener("pessoa-selected", (e) => {
        this.pessoaIds = e.detail.selected.map((s) => s.id);
        this.pessoasSelecionadas = e.detail.selected;
        // Buscar endereços das pessoas selecionadas
        for (const p of e.detail.selected) {
          if (!this.pessoaEnderecos[p.id]) {
            this.carregarEnderecos(p.id);
          }
        }
      });
      this.$el.addEventListener("veiculo-selected", (e) => {
        this.veiculoIds = e.detail.selected.map((s) => s.id);
        this.veiculosSelecionados = e.detail.selected;
      });

      // Escutar pedido de abrir cadastro de veículo (vindo do autocomplete)
      this.$el.addEventListener("abrir-cadastro-veiculo", (e) => {
        this.showNovoVeiculo = true;
        const q = e.detail?.query || "";
        if (q) this.novoVeiculo.placa = q;
      });

      // Escutar pedido de abrir cadastro (vindo do autocomplete)
      this.$el.addEventListener("abrir-cadastro-pessoa", (e) => {
        this.showNovaPessoa = true;
        // Preencher nome com o que foi buscado (se não for CPF)
        const q = e.detail?.query || "";
        if (q && !/^\d/.test(q)) {
          this.novaPessoa.nome = q;
        } else if (q && /^\d/.test(q)) {
          this.novaPessoa.cpf = q;
        }
      });
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroPessoa = "Nome é obrigatório.";
        return;
      }

      this.salvandoPessoa = true;
      this.erroPessoa = null;

      try {
        // Criar pessoa
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) {
          pessoaData.cpf = this.novaPessoa.cpf.trim();
        }
        if (this.novaPessoa.data_nascimento) {
          pessoaData.data_nascimento = this.novaPessoa.data_nascimento;
        }
        if (this.novaPessoa.apelido.trim()) {
          pessoaData.apelido = this.novaPessoa.apelido.trim();
        }

        const pessoa = await api.post("/pessoas/", pessoaData);

        // Criar endereço se preenchido
        if (this.novaPessoa.endereco.trim() || this.novaPessoa.bairro.trim() || this.novaPessoa.cidade.trim() || this.novaPessoa.estado.trim()) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            bairro: this.novaPessoa.bairro.trim() || null,
            cidade: this.novaPessoa.cidade.trim() || null,
            estado: this.novaPessoa.estado.trim().toUpperCase() || null,
          });
        }

        // Adicionar à lista de abordados
        this.pessoaIds.push(pessoa.id);
        this.pessoasSelecionadas.push(pessoa);

        // Atualizar tags do autocomplete
        const autocompleteEl = this.$el.querySelector("[x-data*='autocompleteComponent']");
        if (autocompleteEl?._x_dataStack) {
          autocompleteEl._x_dataStack[0].selected.push(pessoa);
        }

        // Reset formulário
        this.novaPessoa = { nome: "", cpf: "", endereco: "", bairro: "", cidade: "", estado: "" };
        this.showNovaPessoa = false;
      } catch (err) {
        this.erroPessoa = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },

    async carregarEnderecos(pessoaId) {
      try {
        const detalhe = await api.get(`/pessoas/${pessoaId}`);
        this.pessoaEnderecos = { ...this.pessoaEnderecos, [pessoaId]: detalhe.enderecos || [] };
      } catch { /* silencioso */ }
    },

    async salvarNovoEndereco(pessoaId) {
      const endereco = this.novoEnderecoData[pessoaId + "_endereco"]?.trim();
      if (!endereco) return;

      this.salvandoEndereco = { ...this.salvandoEndereco, [pessoaId]: true };
      this.erroEndereco = { ...this.erroEndereco, [pessoaId]: null };

      try {
        await api.post(`/pessoas/${pessoaId}/enderecos`, {
          endereco: endereco,
          bairro: this.novoEnderecoData[pessoaId + "_bairro"]?.trim() || null,
          cidade: this.novoEnderecoData[pessoaId + "_cidade"]?.trim() || null,
          estado: this.novoEnderecoData[pessoaId + "_estado"]?.trim().toUpperCase() || null,
        });

        // Recarregar endereços e fechar form
        await this.carregarEnderecos(pessoaId);
        this.novoEnderecoAberto = { ...this.novoEnderecoAberto, [pessoaId]: false };
        this.novoEnderecoData = {
          ...this.novoEnderecoData,
          [pessoaId + "_endereco"]: "",
          [pessoaId + "_bairro"]: "",
          [pessoaId + "_cidade"]: "",
          [pessoaId + "_estado"]: "",
        };
      } catch (err) {
        this.erroEndereco = { ...this.erroEndereco, [pessoaId]: err.message || "Erro ao salvar endereço." };
      } finally {
        this.salvandoEndereco = { ...this.salvandoEndereco, [pessoaId]: false };
      }
    },

    formatEndereco(end) {
      if (!end) return "";
      const parts = [end.endereco, end.bairro, end.cidade, end.estado].filter(Boolean);
      return parts.join(", ");
    },

    async criarVeiculo() {
      const placa = this.novoVeiculo.placa.trim();
      if (!placa) {
        this.erroVeiculo = "Placa é obrigatória.";
        return;
      }

      this.salvandoVeiculo = true;
      this.erroVeiculo = null;

      try {
        const veiculoData = { placa };
        if (this.novoVeiculo.modelo.trim()) veiculoData.modelo = this.novoVeiculo.modelo.trim();
        if (this.novoVeiculo.cor.trim()) veiculoData.cor = this.novoVeiculo.cor.trim();
        if (this.novoVeiculo.ano) veiculoData.ano = parseInt(this.novoVeiculo.ano);

        const veiculo = await api.post("/veiculos/", veiculoData);

        // Adicionar à lista de veículos da abordagem
        this.veiculoIds.push(veiculo.id);
        this.veiculosSelecionados.push(veiculo);

        // Atualizar tags do autocomplete de veículo (segundo autocomplete na seção)
        const veiculoAutoEl = this.$el.querySelectorAll("[x-data*='autocompleteComponent']")[1];
        if (veiculoAutoEl?._x_dataStack) {
          veiculoAutoEl._x_dataStack[0].selected.push(veiculo);
        }

        // Reset (fotoVeiculoFile mantida — será enviada no submit() com o abordagem_id)
        this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
        this.showNovoVeiculo = false;
      } catch (err) {
        this.erroVeiculo = err.message || "Erro ao cadastrar veículo.";
      } finally {
        this.salvandoVeiculo = false;
      }
    },

    async captureGPS() {
      this.gpsLoading = true;
      try {
        const loc = await getGPSLocation();
        this.latitude = loc.latitude;
        this.longitude = loc.longitude;
        this.endereco = loc.endereco_texto || "";
      } catch {
        this.endereco = "";
      } finally {
        this.gpsLoading = false;
      }
    },

    toggleVoice() {
      if (this.recording) {
        stopVoice();
        this.recording = false;
      } else {
        startVoice(
          (text, isFinal) => {
            if (isFinal) {
              this.observacao += (this.observacao ? " " : "") + text;
            }
          },
          () => { this.recording = false; }
        );
        this.recording = true;
      }
    },

    onFotoVeiculoSelected(event) {
      this.fotoVeiculoFile = event.target.files[0] || null;
    },

    async submit() {
      if (this.submitting) return;
      this.submitting = true;
      this.erro = null;
      this.sucesso = null;

      // Gerar client_id único para deduplicação (idempotência)
      if (!this.clientId) {
        this.clientId = crypto.randomUUID();
      }

      const obsTexto = this.observacao || "";

      const payload = {
        data_hora: new Date().toISOString(),
        latitude: this.latitude,
        longitude: this.longitude,
        endereco_texto: this.endereco || null,
        observacao: obsTexto || null,
        origem: navigator.onLine ? "online" : "offline",
        client_id: this.clientId,
        pessoa_ids: this.pessoaIds,
        veiculo_ids: this.veiculoIds,
        passagens: [],
      };

      try {
        if (navigator.onLine) {
          const result = await api.post("/abordagens/", payload);

          // Upload foto de cada abordado
          for (const [pessoaId, file] of Object.entries(this.fotosPessoas)) {
            if (file) {
              await api.uploadFile("/fotos/upload", file, {
                tipo: "rosto",
                pessoa_id: parseInt(pessoaId),
                abordagem_id: result.id,
              });
            }
          }

          // Upload foto do veículo se houver
          if (this.fotoVeiculoFile && result.id) {
            await api.uploadFile("/fotos/upload", this.fotoVeiculoFile, {
              tipo: "veiculo",
              abordagem_id: result.id,
            });
          }

          this.sucesso = `Abordagem #${result.id} registrada com sucesso!`;
        } else {
          // Salvar offline
          await enqueueSync("abordagem", payload);
          this.sucesso = "Abordagem salva na fila offline. Será sincronizada automaticamente.";
          // Atualizar contador de pendentes
          const appEl = document.querySelector("[x-data]");
          if (appEl?._x_dataStack) appEl._x_dataStack[0]._updateSyncCount();
        }

        // Reset form
        this.clientId = null;
        this.observacao = "";
        this.pessoaIds = [];
        this.pessoasSelecionadas = [];
        this.fotosPessoas = {};
        this.pessoaEnderecos = {};
        this.novoEnderecoAberto = {};
        this.novoEnderecoData = {};
        this.veiculoIds = [];
        this.veiculosSelecionados = [];
        this.veiculoPorPessoa = {};
        this.fotoVeiculoFile = null;
      } catch (err) {
        this.erro = err.message || "Erro ao registrar abordagem.";
      } finally {
        this.submitting = false;
      }
    },
  };
}
