/**
 * Página de consulta unificada — Argus AI.
 *
 * Todos os filtros em uma única página: nome/CPF, localização
 * e veículo. Busca paralela nas entidades relevantes conforme
 * os campos preenchidos.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- Pessoa -->
      <div class="space-y-2">
        <label class="block text-sm text-slate-300 font-semibold">Pessoa</label>
        <div class="relative">
          <input type="text" x-model="query" @input="onInput()"
                 placeholder="Nome completo ou CPF..."
                 class="w-full pl-12 py-3 text-base">
          <svg class="absolute left-3.5 top-3.5 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>
      </div>

      <!-- Endereço -->
      <div class="space-y-2">
        <label class="block text-sm text-slate-300 font-semibold">Endereço</label>
        <div class="grid grid-cols-3 gap-2">
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
      </div>

      <!-- Veículo -->
      <div class="space-y-2">
        <label class="block text-sm text-slate-300 font-semibold">Veículo</label>
        <div class="grid gap-2" :class="filtroModelo.length > 0 ? 'grid-cols-3' : 'grid-cols-2'">
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
      </div>

      <!-- Spinner -->
      <div x-show="loading" class="flex justify-center py-2">
        <span class="spinner"></span>
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
      <div x-show="searched && veiculosFiltrados.length > 0">
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
      try {
        const tarefas = [];

        // Busca pessoas: por nome/CPF e/ou endereço
        const buscaPessoa =
          this.query.length >= 2 ||
          this.filtroBairro.length >= 2 ||
          this.filtroCidade.length >= 2 ||
          this.filtroEstado.length >= 1;

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
        if (this.filtroPlaca.length >= 2) {
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
