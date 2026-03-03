/**
 * Página de consulta unificada — Argus AI.
 *
 * Busca por três domínios separados via abas:
 * - Pessoa: busca por nome ou CPF
 * - Endereço: filtros de bairro, cidade e estado com autocomplete
 * - Veículo: busca por placa com filtros de modelo e cor
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- Abas -->
      <div class="flex gap-1 bg-slate-800/60 p-1 rounded-lg">
        <button type="button" @click="trocarAba('pessoa')"
                class="flex-1 text-sm py-1.5 rounded-md transition-colors"
                :class="aba === 'pessoa' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'">
          Pessoa
        </button>
        <button type="button" @click="trocarAba('endereco')"
                class="flex-1 text-sm py-1.5 rounded-md transition-colors"
                :class="aba === 'endereco' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'">
          Endereço
        </button>
        <button type="button" @click="trocarAba('veiculo')"
                class="flex-1 text-sm py-1.5 rounded-md transition-colors"
                :class="aba === 'veiculo' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'">
          Veículo
        </button>
      </div>

      <!-- Aba: Pessoa -->
      <div x-show="aba === 'pessoa'">
        <div class="relative">
          <input type="text" x-model="query" @input="onInput()"
                 placeholder="Nome completo ou CPF..."
                 class="w-full pl-10">
          <svg class="absolute left-3 top-3 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/>
          </svg>
          <span x-show="loading" class="absolute right-3 top-3"><span class="spinner"></span></span>
        </div>
      </div>

      <!-- Aba: Endereço -->
      <div x-show="aba === 'endereco'" class="space-y-2">
        <div class="grid grid-cols-3 gap-2">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Bairro</label>
            <input type="text" list="lista-bairros-consulta" x-model="filtroBairro" @input="onInput()"
                   placeholder="Bairro..." class="w-full text-sm">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Cidade</label>
            <input type="text" list="lista-cidades-consulta" x-model="filtroCidade" @input="onInput()"
                   placeholder="Cidade..." class="w-full text-sm">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
            <input type="text" list="lista-estados-consulta" x-model="filtroEstado" @input="onInput()"
                   placeholder="DF" maxlength="2" class="w-full text-sm uppercase">
          </div>
        </div>
        <div class="flex justify-center" x-show="loading"><span class="spinner"></span></div>
        <datalist id="lista-bairros-consulta">
          <template x-for="b in localidades.bairros" :key="b"><option :value="b"></option></template>
        </datalist>
        <datalist id="lista-cidades-consulta">
          <template x-for="c in localidades.cidades" :key="c"><option :value="c"></option></template>
        </datalist>
        <datalist id="lista-estados-consulta">
          <template x-for="e in localidades.estados" :key="e"><option :value="e"></option></template>
        </datalist>
      </div>

      <!-- Aba: Veículo -->
      <div x-show="aba === 'veiculo'" class="space-y-2">
        <div class="relative">
          <input type="text" x-model="filtroPlaca" @input="onInput()"
                 placeholder="Placa (ex: ABC1234)..." maxlength="10"
                 class="w-full pl-10 uppercase" style="text-transform:uppercase">
          <svg class="absolute left-3 top-3 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/>
          </svg>
          <span x-show="loading" class="absolute right-3 top-3"><span class="spinner"></span></span>
        </div>
        <input type="text" x-model="filtroModelo" @input="onInput()"
               placeholder="Modelo (opcional)..." class="w-full text-sm">
        <div x-show="filtroModelo.length > 0">
          <input type="text" x-model="filtroCor" @input="onInput()"
                 placeholder="Cor (opcional)..." class="w-full text-sm">
        </div>
      </div>

      <!-- Resultados: Pessoas -->
      <div x-show="searched && pessoasVisiveis.length > 0">
        <h3 class="text-sm font-semibold text-slate-400 mb-2">
          Pessoas (<span x-text="pessoasVisiveis.length"></span>)
        </h3>
        <div class="space-y-2">
          <template x-for="p in pessoasVisiveis" :key="p.id">
            <div @click="viewPessoa(p.id)" class="card cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Apelido: ' + p.apelido"></p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Resultados: Veículos -->
      <div x-show="aba === 'veiculo' && searched && veiculosFiltrados.length > 0">
        <h3 class="text-sm font-semibold text-slate-400 mb-2">
          Veículos (<span x-text="veiculosFiltrados.length"></span>)
        </h3>
        <div class="space-y-2">
          <template x-for="v in veiculosFiltrados" :key="v.id">
            <div class="card space-y-1">
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="v.placa"></span>
                <span x-show="v.tipo" class="text-xs text-slate-500 bg-slate-700 px-2 py-0.5 rounded" x-text="v.tipo"></span>
              </div>
              <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
                 x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
              <p x-show="v.observacoes" class="text-xs text-slate-500 line-clamp-2" x-text="v.observacoes"></p>
              <!-- Pessoa vinculada (extraída da observação da abordagem) -->
              <div x-show="vinculoPorVeiculo[v.placa]" class="flex items-center gap-1 pt-0.5">
                <svg class="w-3 h-3 text-blue-400 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                </svg>
                <span class="text-xs text-blue-400" x-text="vinculoPorVeiculo[v.placa]"></span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Sem resultados -->
      <p x-show="searched && !loading && semResultados"
         class="text-sm text-slate-500 text-center py-8">
        Nenhum resultado encontrado.
      </p>
    </div>
  `;
}

function consultaPage() {
  return {
    aba: "pessoa",

    // Campos de busca
    query: "",
    filtroBairro: "",
    filtroCidade: "",
    filtroEstado: "",
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",

    localidades: { bairros: [], cidades: [], estados: [] },
    results: {},
    vinculoPorVeiculo: {},
    loading: false,
    searched: false,
    _timer: null,

    // --- computed ---

    get pessoasVisiveis() {
      if (this.aba === "veiculo") return [];
      return this.results.pessoas || [];
    },

    get veiculosFiltrados() {
      const vs = this.results.veiculos || [];
      return vs.filter((v) => {
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
      if (this.aba === "veiculo") return this.veiculosFiltrados.length === 0;
      return this.pessoasVisiveis.length === 0;
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

    trocarAba(novaAba) {
      this.aba = novaAba;
      this.query = "";
      this.filtroBairro = "";
      this.filtroCidade = "";
      this.filtroEstado = "";
      this.filtroPlaca = "";
      this.filtroModelo = "";
      this.filtroCor = "";
      this.results = {};
      this.vinculoPorVeiculo = {};
      this.searched = false;
      clearTimeout(this._timer);
    },

    onInput() {
      clearTimeout(this._timer);
      if (!this._pronto()) {
        this.results = {};
        this.searched = false;
        return;
      }
      this._timer = setTimeout(() => this.search(), 400);
    },

    _pronto() {
      if (this.aba === "pessoa") return this.query.length >= 2;
      if (this.aba === "endereco")
        return (
          this.filtroBairro.length >= 2 ||
          this.filtroCidade.length >= 2 ||
          this.filtroEstado.length >= 1
        );
      if (this.aba === "veiculo") return this.filtroPlaca.length >= 2;
      return false;
    },

    async search() {
      this.loading = true;
      try {
        if (this.aba === "pessoa") {
          this.results = await api.get(
            `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`
          );
        } else if (this.aba === "endereco") {
          let url = "/consultas/?q=a&tipo=pessoa";
          if (this.filtroBairro.length >= 2)
            url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
          if (this.filtroCidade.length >= 2)
            url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
          if (this.filtroEstado.length >= 1)
            url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
          this.results = await api.get(url);
        } else if (this.aba === "veiculo") {
          this.results = await api.get(
            `/consultas/?q=${encodeURIComponent(this.filtroPlaca)}&tipo=veiculo`
          );
          this._extrairVinculos();
        }
        this.searched = true;
      } catch {
        showToast("Erro na busca", "error");
      } finally {
        this.loading = false;
      }
    },

    _extrairVinculos() {
      // Extrai vínculos veículo→pessoa da observação das abordagens retornadas.
      // Formato armazenado: "Vínculos: ABC1234 → João Silva, XYZ5678 → Maria"
      const vinculos = {};
      for (const a of this.results.abordagens || []) {
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
