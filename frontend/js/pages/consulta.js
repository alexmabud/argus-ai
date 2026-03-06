/**
 * Página de consulta unificada — Argus AI.
 *
 * Todos os filtros em uma única página: nome/CPF, localização
 * e veículo. Busca paralela nas entidades relevantes conforme
 * os campos preenchidos. Resultados aparecem logo abaixo de
 * cada seção de busca correspondente.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- Pessoa -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Pessoa</p>
        <div class="relative">
          <input type="text" x-model="query" @input="onInput()"
                 placeholder="Nome completo ou CPF..."
                 class="w-full pl-12 py-3 text-base">
          <svg class="absolute left-3.5 top-3.5 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>

        <!-- Resultados: Pessoas (por nome/CPF) -->
        <div x-show="searched && pessoasVisiveis.length > 0 && buscouPessoa" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Resultados (<span x-text="pessoasVisiveis.length"></span>)
          </p>
          <template x-for="p in pessoasVisiveis" :key="p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
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

        <!-- Sem resultados pessoa -->
        <p x-show="searched && !loading && buscouPessoa && pessoasVisiveis.length === 0 && !buscouEndereco"
           class="text-xs text-slate-500 pt-1">
          Nenhuma pessoa encontrada.
        </p>
      </div>

      <!-- Separador Ou -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- Endereço -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Endereço</p>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-xs text-slate-500 mb-1">Bairro</label>
            <input type="text" list="lista-bairros-c" x-model="filtroBairro" @input="onInput()"
                   placeholder="Bairro..." class="w-full py-3">
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Cidade</label>
            <input type="text" list="lista-cidades-c" x-model="filtroCidade" @input="onInput()"
                   placeholder="Cidade..." class="w-full py-3">
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Estado (UF)</label>
            <input type="text" list="lista-estados-c" x-model="filtroEstado" @input="onInput()"
                   placeholder="DF" maxlength="2" class="w-full py-3 uppercase">
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

        <!-- Resultados: Pessoas (por endereço) -->
        <div x-show="searched && pessoasVisiveis.length > 0 && buscouEndereco" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Pessoas neste endereço (<span x-text="pessoasVisiveis.length"></span>)
          </p>
          <template x-for="p in pessoasVisiveis" :key="p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
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

        <!-- Sem resultados endereço -->
        <p x-show="searched && !loading && buscouEndereco && pessoasVisiveis.length === 0 && !buscouPessoa"
           class="text-xs text-slate-500 pt-1">
          Nenhuma pessoa encontrada neste endereço.
        </p>
      </div>

      <!-- Separador Ou -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- Veículo -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Veículo</p>
        <div class="grid gap-3" :class="filtroModelo.length > 0 ? 'grid-cols-3' : 'grid-cols-2'">
          <div>
            <label class="block text-xs text-slate-500 mb-1">Placa</label>
            <input type="text" x-model="filtroPlaca" @input="onInput()"
                   placeholder="ABC1234..." maxlength="10"
                   class="w-full py-3 uppercase" style="text-transform:uppercase">
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Modelo</label>
            <input type="text" x-model="filtroModelo" @input="onInput()"
                   placeholder="Modelo..." class="w-full py-3">
          </div>
          <div x-show="filtroModelo.length > 0">
            <label class="block text-xs text-slate-500 mb-1">Cor</label>
            <input type="text" x-model="filtroCor" @input="onInput()"
                   placeholder="Cor..." class="w-full py-3">
          </div>
        </div>

        <!-- Resultados: Veículos -->
        <div x-show="searched && veiculosFiltrados.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Resultados (<span x-text="veiculosFiltrados.length"></span>)
          </p>
          <template x-for="v in veiculosFiltrados" :key="v.id">
            <div class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 space-y-1">
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="v.placa"></span>
                <span x-show="v.tipo" class="text-xs text-slate-500 bg-slate-700 px-2 py-0.5 rounded" x-text="v.tipo"></span>
              </div>
              <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
                 x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
              <p x-show="v.criado_em" class="text-xs text-slate-500"
                 x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></p>
              <div x-show="vinculoPorVeiculo[v.placa]" class="flex items-center gap-1 pt-0.5">
                <svg class="w-3 h-3 text-blue-400 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                </svg>
                <span class="text-xs text-blue-400" x-text="vinculoPorVeiculo[v.placa]"></span>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados veículo -->
        <p x-show="searched && !loading && buscouVeiculo && veiculosFiltrados.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhum veículo encontrado.
        </p>
      </div>

      <!-- Spinner -->
      <div x-show="loading" class="flex justify-center py-2">
        <span class="spinner"></span>
      </div>
    </div>
  `;
}

function consultaPage() {
  return {
    query: "",
    filtroBairro: "",
    filtroCidade: "",
    filtroEstado: "",
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",

    localidades: { bairros: [], cidades: [], estados: [] },
    pessoas: [],
    veiculos: [],
    vinculoPorVeiculo: {},
    loading: false,
    searched: false,
    buscouPessoa: false,
    buscouEndereco: false,
    buscouVeiculo: false,
    _timer: null,

    // --- computed ---

    get pessoasVisiveis() {
      return this.pessoas;
    },

    get veiculosFiltrados() {
      return this.veiculos.filter((v) => {
        if (
          this.filtroModelo.length > 0 &&
          !(v.modelo || "").toLowerCase().includes(this.filtroModelo.toLowerCase())
        )
          return false;
        if (
          this.filtroCor.length > 0 &&
          !(v.cor || "").toLowerCase().includes(this.filtroCor.toLowerCase())
        )
          return false;
        return true;
      });
    },

    get semResultados() {
      return this.pessoasVisiveis.length === 0 && this.veiculosFiltrados.length === 0;
    },

    // --- lifecycle ---

    async init() {
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch {
        /* silencioso */
      }
    },

    // --- actions ---

    onInput() {
      clearTimeout(this._timer);
      if (!this._algumCampoPreenchido()) {
        this.pessoas = [];
        this.veiculos = [];
        this.vinculoPorVeiculo = {};
        this.searched = false;
        this.buscouPessoa = false;
        this.buscouEndereco = false;
        this.buscouVeiculo = false;
        return;
      }
      this._timer = setTimeout(() => this.search(), 400);
    },

    _algumCampoPreenchido() {
      return (
        this.query.length >= 2 ||
        this.filtroBairro.length >= 2 ||
        this.filtroCidade.length >= 2 ||
        this.filtroEstado.length >= 1 ||
        this.filtroPlaca.length >= 2
      );
    },

    async search() {
      this.loading = true;
      this.buscouPessoa = this.query.length >= 2;
      this.buscouEndereco = this.filtroBairro.length >= 2 || this.filtroCidade.length >= 2 || this.filtroEstado.length >= 1;
      this.buscouVeiculo = this.filtroPlaca.length >= 2;

      try {
        const tarefas = [];

        // Busca pessoas: por nome/CPF e/ou endereço
        const buscaPessoa = this.buscouPessoa || this.buscouEndereco;

        if (buscaPessoa) {
          const q = this.query.length >= 2 ? this.query : "a";
          let url = `/consultas/?q=${encodeURIComponent(q)}&tipo=pessoa`;
          if (this.filtroBairro.length >= 2)
            url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
          if (this.filtroCidade.length >= 2)
            url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
          if (this.filtroEstado.length >= 1)
            url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
          tarefas.push(api.get(url).then((r) => { this.pessoas = r.pessoas || []; }));
        } else {
          this.pessoas = [];
        }

        // Busca veículos: por placa
        if (this.buscouVeiculo) {
          const url = `/consultas/?q=${encodeURIComponent(this.filtroPlaca)}&tipo=veiculo`;
          tarefas.push(
            api.get(url).then((r) => {
              this.veiculos = r.veiculos || [];
              this._extrairVinculos(r.abordagens || []);
            })
          );
        } else {
          this.veiculos = [];
          this.vinculoPorVeiculo = {};
        }

        await Promise.all(tarefas);
        this.searched = true;
      } catch {
        showToast("Erro na busca", "error");
      } finally {
        this.loading = false;
      }
    },

    _extrairVinculos(abordagens) {
      const vinculos = {};
      for (const a of abordagens) {
        if (!a.observacao) continue;
        const match = a.observacao.match(/V[ií]nculos?:\s*(.+)/i);
        if (!match) continue;
        for (const par of match[1].split(",")) {
          const partes = par.split("→").map((s) => s.trim());
          if (partes.length === 2 && partes[0] && partes[1]) {
            vinculos[partes[0].toUpperCase()] = partes[1];
          }
        }
      }
      this.vinculoPorVeiculo = vinculos;
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0].currentPage = "pessoa-detalhe";
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },
  };
}
