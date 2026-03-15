/**
 * Página de consulta unificada — Argus AI.
 *
 * Seções independentes: busca de pessoa (nome/CPF ou foto),
 * filtros por endereço e busca por veículo. Cada seção retorna
 * a ficha do abordado como resultado.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- ── Pessoa ─────────────────────────────────────────── -->
      <div class="card space-y-3">
        <div class="flex items-center justify-between">
          <p class="text-sm font-semibold text-slate-300">Pessoa</p>
          <button @click="showCadastroPessoa = !showCadastroPessoa; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; fotoPessoa = null; erroCadastro = null"
                  class="text-xs text-blue-400 hover:text-blue-300">
            + Nova Pessoa
          </button>
        </div>

        <!-- Campo texto -->
        <div class="relative">
          <input type="text" :value="query"
                 @input="query = formatarBuscaQuery($event.target.value); onInput()"
                 placeholder="Nome completo ou CPF..."
                 inputmode="text"
                 class="w-full pl-12 py-3 text-base">
          <svg class="absolute left-3.5 top-3.5 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>

        <!-- Separador ou -->
        <div class="flex items-center gap-3">
          <div class="flex-1 h-px bg-slate-700"></div>
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
          <div class="flex-1 h-px bg-slate-700"></div>
        </div>

        <!-- Zona de busca por foto -->
        <button x-show="!fotoFile" @click="$refs.fotoInput.click()"
                class="w-full flex flex-col items-center gap-2 py-4 px-3 rounded-xl border-2 border-dashed border-indigo-500/50 bg-indigo-500/5 hover:bg-indigo-500/10 hover:border-indigo-400 transition-all active:scale-95">
          <div class="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-500/15 text-indigo-400">
            <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/>
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/>
            </svg>
          </div>
          <div class="text-center">
            <p class="text-sm font-semibold text-indigo-300">Reconhecimento Facial</p>
            <p class="text-xs text-slate-500 mt-0.5">Toque para enviar uma foto e comparar com o banco</p>
          </div>
        </button>
        <input type="file" x-ref="fotoInput" accept="image/jpeg,image/png,image/webp"
               class="hidden" @change="onFotoSelect($event)">

        <!-- Preview da foto -->
        <div x-show="fotoFile" class="flex items-center gap-3 p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/30">
          <img :src="fotoPreviewUrl" class="w-12 h-12 rounded object-cover shrink-0">
          <div class="flex-1 min-w-0">
            <p class="text-xs text-indigo-300 font-medium truncate" x-text="fotoFile?.name"></p>
            <p class="text-xs text-slate-500">Comparando rosto com o banco...</p>
          </div>
          <button @click="removeFoto()" class="p-1 text-slate-500 hover:text-red-400 transition-colors">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Resultados: Pessoas por texto -->
        <div x-show="searched && pessoasTexto.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">Resultados por nome/CPF (<span x-text="pessoasTexto.length"></span>)</p>
          <template x-for="p in pessoasTexto" :key="'t-' + p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center gap-3">
                <!-- Avatar -->
                <template x-if="p.foto_principal_url">
                  <img :src="p.foto_principal_url" class="w-8 h-8 rounded-full object-cover shrink-0">
                </template>
                <template x-if="!p.foto_principal_url">
                  <div class="w-8 h-8 rounded-full bg-slate-700 shrink-0 flex items-center justify-center text-slate-500">
                    <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                    </svg>
                  </div>
                </template>
                <!-- Texto -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Resultados: Pessoas por foto -->
        <div x-show="pessoasFoto.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">Resultados por foto (<span x-text="pessoasFoto.length"></span>)</p>
          <template x-for="r in pessoasFoto" :key="'f-' + r.foto_id">
            <div @click="r.pessoa_id && viewPessoa(r.pessoa_id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                  <img x-show="r.foto_principal_url || r.arquivo_url" :src="r.foto_principal_url || r.arquivo_url"
                       class="w-10 h-10 rounded-full object-cover shrink-0">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-slate-200" x-text="r.nome || 'Pessoa sem nome'"></p>
                    <p x-show="r.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + r.cpf_masked"></p>
                    <p x-show="r.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + r.apelido"></p>
                    <!-- Barra de confiança -->
                    <div class="mt-1.5 flex items-center gap-2">
                      <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all"
                             :style="'width: ' + Math.round(r.similaridade * 100) + '%'"
                             :class="r.similaridade >= 0.8 ? 'bg-green-500' : r.similaridade >= 0.6 ? 'bg-yellow-500' : 'bg-orange-500'">
                        </div>
                      </div>
                      <span class="text-xs font-mono shrink-0"
                            :class="r.similaridade >= 0.8 ? 'text-green-400' : r.similaridade >= 0.6 ? 'text-yellow-400' : 'text-orange-400'"
                            x-text="Math.round(r.similaridade * 100) + '%'">
                      </span>
                    </div>
                  </div>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0 ml-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados por foto -->
        <p x-show="fotoSearchDone && !loadingPessoa && fotoServicoIndisponivel"
           class="text-xs text-amber-500 pt-1">
          Reconhecimento facial indisponível neste servidor.
        </p>
        <p x-show="fotoSearchDone && !loadingPessoa && !fotoServicoIndisponivel && pessoasFoto.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhuma correspondência facial encontrada.
        </p>

        <!-- Sem resultados pessoa -->
        <div x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0 && !fotoSearchDone"
             class="pt-1">
          <p class="text-xs text-slate-500 inline">Nenhuma pessoa encontrada. </p>
          <button @click="showCadastroPessoa = true; if (query && !/^\d/.test(query)) novaPessoa.nome = query; else if (query) novaPessoa.cpf = query"
                  class="text-xs text-blue-400 hover:text-blue-300 font-medium">
            Cadastrar
          </button>
        </div>

        <!-- Formulário inline: cadastrar nova pessoa -->
        <div x-show="showCadastroPessoa" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-4 space-y-3 mt-2">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-slate-200">Cadastrar nova pessoa</h3>
            <button @click="showCadastroPessoa = false; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; fotoPessoa = null; erroCadastro = null"
                    class="text-slate-400 hover:text-white text-xs">Cancelar</button>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo" class="w-full">
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">CPF</label>
            <input type="text" :value="novaPessoa.cpf"
                   @input="novaPessoa.cpf = formatarCPF($event.target.value)"
                   placeholder="000.000.000-00" maxlength="14" inputmode="numeric" class="w-full">
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
              <input type="text" list="lista-bairros-c" x-model="novaPessoa.bairro" placeholder="Bairro" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Cidade</label>
              <input type="text" list="lista-cidades-c" x-model="novaPessoa.cidade" placeholder="Cidade" class="w-full">
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
              <input type="text" list="lista-estados-c" x-model="novaPessoa.estado" placeholder="DF" maxlength="2" class="w-full uppercase">
            </div>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Foto</label>
            <input type="file" accept="image/*" capture="environment"
                   @change="fotoPessoa = $event.target.files[0] || null"
                   class="text-sm text-slate-400 w-full">
            <p x-show="fotoPessoa" class="text-xs text-slate-500 mt-1" x-text="fotoPessoa?.name"></p>
          </div>

          <button @click="criarPessoa()" class="btn btn-primary text-sm w-full"
                  :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
            <span x-show="!salvandoPessoa">Salvar pessoa</span>
            <span x-show="salvandoPessoa" class="flex items-center justify-center gap-2">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroCadastro" class="text-xs text-red-400" x-text="erroCadastro"></p>
        </div>

        <!-- Spinner pessoa -->
        <div x-show="loadingPessoa" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>

      <!-- ── Separador ───────────────────────────────────────── -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- ── Filtros por Endereço ───────────────────────────── -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Filtros por Endereço</p>
        <p class="text-xs text-slate-500">Filtre abordados pelo local de residência cadastrado.</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Bairro</label>
            <input type="text" list="lista-bairros-c" x-model="filtroBairro" @input="onInputEndereco()"
                   placeholder="Bairro..." class="w-full py-3">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados deste bairro</p>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Cidade</label>
            <input type="text" list="lista-cidades-c" x-model="filtroCidade" @input="onInputEndereco()"
                   placeholder="Cidade..." class="w-full py-3">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados desta cidade</p>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
            <input type="text" list="lista-estados-c" x-model="filtroEstado" @input="onInputEndereco()"
                   placeholder="DF" maxlength="2" class="w-full py-3 uppercase">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados deste estado</p>
          </div>
        </div>

        <datalist id="lista-bairros-c">
          <template x-for="b in localidades.bairros" :key="b"><option :value="b"></option></template>
        </datalist>
        <datalist id="lista-cidades-c">
          <template x-for="c in localidades.cidades" :key="c"><option :value="c"></option></template>
        </datalist>
        <datalist id="lista-estados-c">
          <template x-for="e in localidades.estados" :key="e"><option :value="e"></option></template>
        </datalist>

        <!-- Resultados por endereço -->
        <div x-show="searchedEndereco && pessoasEndereco.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Pessoas neste endereço (<span x-text="pessoasEndereco.length"></span>)
          </p>
          <template x-for="p in pessoasEndereco" :key="'e-' + p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                  <p x-show="p.endereco_criado_em" class="text-xs text-slate-500"
                     x-text="'Endereço cadastrado em ' + new Date(p.endereco_criado_em).toLocaleDateString('pt-BR')"></p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados endereço -->
        <p x-show="searchedEndereco && !loadingEndereco && pessoasEndereco.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhuma pessoa encontrada neste endereço.
        </p>

        <!-- Spinner endereço -->
        <div x-show="loadingEndereco" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>

      <!-- ── Separador ───────────────────────────────────────── -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- ── Buscar por Veículo ─────────────────────────────── -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Buscar por Veículo</p>
        <p class="text-xs text-slate-500">Encontre o abordado pelo veículo com que foi visto.</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Placa</label>
            <input type="text" :value="filtroPlaca"
                   @input="filtroPlaca = formatarPlaca($event.target.value); onInputVeiculo()"
                   placeholder="ABC-1234..." maxlength="8"
                   class="w-full py-3 uppercase" style="text-transform:uppercase">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Modelo</label>
            <input type="text" x-model="filtroModelo" @input="onInputVeiculo()"
                   placeholder="Modelo do veículo..." class="w-full py-3">
          </div>
          <div x-show="filtroModelo.length > 0">
            <label class="block text-xs text-slate-400 mb-1">Cor <span class="text-slate-600">(opcional)</span></label>
            <input type="text" x-model="filtroCor" @input="onInputVeiculo()"
                   placeholder="Cor do veículo..." class="w-full py-3">
          </div>
        </div>

        <!-- Resultados: fichas de abordados por veículo -->
        <div x-show="searchedVeiculo && pessoasVeiculo.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Abordados vinculados (<span x-text="pessoasVeiculo.length"></span>)
          </p>
          <template x-for="p in pessoasVeiculo" :key="'v-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                  <p x-show="p.veiculo_info" class="text-xs text-slate-500 mt-0.5"
                     x-text="'Vinculado via: ' + [p.veiculo_info?.placa, p.veiculo_info?.modelo, p.veiculo_info?.cor, p.veiculo_info?.ano].filter(Boolean).join(' · ')">
                  </p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados veículo -->
        <p x-show="searchedVeiculo && !loadingVeiculo && pessoasVeiculo.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhum abordado vinculado a este veículo.
        </p>

        <!-- Spinner veículo -->
        <div x-show="loadingVeiculo" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>
    </div>
  `;
}

function consultaPage() {
  return {
    // Estado — busca pessoa por texto
    query: "",
    pessoasTexto: [],
    loadingPessoa: false,
    searched: false,
    buscouPessoa: false,
    _timerPessoa: null,

    // Estado — busca por foto
    fotoFile: null,
    fotoPreviewUrl: "",
    pessoasFoto: [],
    fotoSearchDone: false,
    fotoServicoIndisponivel: false,

    // Estado — endereço
    filtroBairro: "",
    filtroCidade: "",
    filtroEstado: "",
    pessoasEndereco: [],
    loadingEndereco: false,
    searchedEndereco: false,
    _timerEndereco: null,

    // Estado — veículo
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",
    pessoasVeiculo: [],
    loadingVeiculo: false,
    searchedVeiculo: false,
    _timerVeiculo: null,

    // Dados auxiliares
    localidades: { bairros: [], cidades: [], estados: [] },

    // Cadastro nova pessoa
    showCadastroPessoa: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" },
    fotoPessoa: null,
    salvandoPessoa: false,
    erroCadastro: null,

    // --- lifecycle ---

    async init() {
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch {
        /* silencioso */
      }
    },

    // --- handlers de input ---

    onInput() {
      clearTimeout(this._timerPessoa);
      if (this.query.length < 2) {
        this.pessoasTexto = [];
        this.searched = false;
        this.buscouPessoa = false;
        return;
      }
      this._timerPessoa = setTimeout(() => this.searchPorTexto(), 400);
    },

    onFotoSelect(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      this.fotoFile = file;
      this.fotoPreviewUrl = URL.createObjectURL(file);
      this.searchPorFoto();
    },

    removeFoto() {
      if (this.fotoPreviewUrl) URL.revokeObjectURL(this.fotoPreviewUrl);
      this.fotoFile = null;
      this.fotoPreviewUrl = "";
      this.pessoasFoto = [];
      this.fotoSearchDone = false;
      this.fotoServicoIndisponivel = false;
      this.$refs.fotoInput.value = "";
    },

    onInputEndereco() {
      clearTimeout(this._timerEndereco);
      const temFiltro = this.filtroBairro.length >= 2 || this.filtroCidade.length >= 2 || this.filtroEstado.length >= 1;
      if (!temFiltro) {
        this.pessoasEndereco = [];
        this.searchedEndereco = false;
        return;
      }
      this._timerEndereco = setTimeout(() => this.searchPorEndereco(), 400);
    },

    onInputVeiculo() {
      clearTimeout(this._timerVeiculo);
      const placaRaw = this.filtroPlaca.replace("-", "");
      const temFiltro = placaRaw.length >= 2 || this.filtroModelo.length >= 2;
      if (!temFiltro) {
        this.pessoasVeiculo = [];
        this.searchedVeiculo = false;
        return;
      }
      this._timerVeiculo = setTimeout(() => this.searchPorVeiculo(), 400);
    },

    // --- métodos de busca ---

    async searchPorTexto() {
      this.loadingPessoa = true;
      this.buscouPessoa = true;
      try {
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`;
        const r = await api.get(url);
        const q = this.query.toLowerCase();
        this.pessoasTexto = (r.pessoas || []).filter(p =>
          (p.nome || "").toLowerCase().includes(q) ||
          (p.apelido || "").toLowerCase().includes(q) ||
          (p.cpf_masked || "").includes(q)
        );
        this.searched = true;
      } catch {
        showToast("Erro na busca por nome/CPF", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorFoto() {
      if (!this.fotoFile) return;
      this.loadingPessoa = true;
      this.fotoSearchDone = false;
      this.fotoServicoIndisponivel = false;
      try {
        const form = new FormData();
        form.append("file", this.fotoFile);
        form.append("top_k", "5");
        const r = await api.postForm("/fotos/buscar-rosto", form);
        this.pessoasFoto = r.resultados || [];
        this.fotoServicoIndisponivel = r.disponivel === false;
        this.fotoSearchDone = true;
      } catch (err) {
        showToast(err?.message || "Erro na busca por foto", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorEndereco() {
      this.loadingEndereco = true;
      try {
        let url = `/consultas/?q=&tipo=pessoa`;
        if (this.filtroBairro.length >= 2) url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
        if (this.filtroCidade.length >= 2) url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
        if (this.filtroEstado.length >= 1) url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
        this.searchedEndereco = true;
      } catch {
        showToast("Erro no filtro por endereço", "error");
      } finally {
        this.loadingEndereco = false;
      }
    },

    async searchPorVeiculo() {
      this.loadingVeiculo = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.length >= 2) params.append("modelo", this.filtroModelo);
        if (this.filtroCor.length >= 1) params.append("cor", this.filtroCor);
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
        this.searchedVeiculo = true;
      } catch {
        showToast("Erro na busca por veículo", "error");
      } finally {
        this.loadingVeiculo = false;
      }
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0].currentPage = "pessoa-detalhe";
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroCadastro = "Nome é obrigatório.";
        return;
      }

      this.salvandoPessoa = true;
      this.erroCadastro = null;

      try {
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) pessoaData.cpf = this.novaPessoa.cpf.trim();
        if (this.novaPessoa.data_nascimento) pessoaData.data_nascimento = this.novaPessoa.data_nascimento;
        if (this.novaPessoa.apelido.trim()) pessoaData.apelido = this.novaPessoa.apelido.trim();

        const pessoa = await api.post("/pessoas/", pessoaData);

        const temEndereco = this.novaPessoa.endereco.trim()
          || this.novaPessoa.bairro.trim()
          || this.novaPessoa.cidade.trim()
          || this.novaPessoa.estado.trim();

        if (temEndereco) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            bairro: this.novaPessoa.bairro.trim() || null,
            cidade: this.novaPessoa.cidade.trim() || null,
            estado: this.novaPessoa.estado.trim().toUpperCase() || null,
          });
        }

        // Upload foto se fornecida
        if (this.fotoPessoa) {
          await api.uploadFile("/fotos/upload", this.fotoPessoa, {
            tipo: "rosto",
            pessoa_id: pessoa.id,
          });
        }

        // Reset e navegar para ficha
        this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
        this.fotoPessoa = null;
        this.showCadastroPessoa = false;
        showToast("Pessoa cadastrada com sucesso!", "success");
        this.viewPessoa(pessoa.id);
      } catch (err) {
        this.erroCadastro = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },
  };
}
