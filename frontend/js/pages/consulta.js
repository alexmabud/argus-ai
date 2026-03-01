/**
 * Página de consulta unificada — Argus AI.
 *
 * Busca cross-domain (pessoas, veículos, abordagens)
 * via endpoint GET /consultas/?q= com resultados agrupados.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- Campo de busca -->
      <div class="relative">
        <input type="text" x-model="query" @input="onInput()"
               placeholder="Buscar pessoa, veículo ou abordagem..."
               class="w-full pl-10">
        <svg class="absolute left-3 top-3 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/>
        </svg>
        <span x-show="loading" class="absolute right-3 top-3"><span class="spinner"></span></span>
      </div>

      <!-- Resultados -->
      <div x-show="searched" class="space-y-4">
        <!-- Pessoas -->
        <div x-show="results.pessoas?.length > 0">
          <h3 class="text-sm font-semibold text-slate-400 mb-2">Pessoas (<span x-text="results.pessoas?.length || 0"></span>)</h3>
          <div class="space-y-2">
            <template x-for="p in results.pessoas" :key="p.id">
              <div @click="viewPessoa(p.id)"
                   class="card cursor-pointer hover:border-blue-500 transition-colors">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                    <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Apelido: ' + p.apelido"></p>
                  </div>
                  <svg class="w-4 h-4 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/></svg>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Veículos -->
        <div x-show="results.veiculos?.length > 0">
          <h3 class="text-sm font-semibold text-slate-400 mb-2">Veículos (<span x-text="results.veiculos?.length || 0"></span>)</h3>
          <div class="space-y-2">
            <template x-for="v in results.veiculos" :key="v.id">
              <div class="card">
                <p class="text-sm font-medium text-slate-200" x-text="v.placa"></p>
                <p x-show="v.modelo" class="text-xs text-slate-400" x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
              </div>
            </template>
          </div>
        </div>

        <!-- Abordagens -->
        <div x-show="results.abordagens?.length > 0">
          <h3 class="text-sm font-semibold text-slate-400 mb-2">Abordagens (<span x-text="results.abordagens?.length || 0"></span>)</h3>
          <div class="space-y-2">
            <template x-for="a in results.abordagens" :key="a.id">
              <div class="card">
                <div class="flex items-center justify-between">
                  <p class="text-sm font-medium text-slate-200" x-text="'#' + a.id + ' — ' + new Date(a.data_hora).toLocaleDateString('pt-BR')"></p>
                </div>
                <p x-show="a.endereco_texto" class="text-xs text-slate-400 mt-1" x-text="a.endereco_texto"></p>
                <p x-show="a.observacao" class="text-xs text-slate-500 mt-1 line-clamp-2" x-text="a.observacao"></p>
              </div>
            </template>
          </div>
        </div>

        <!-- Sem resultados -->
        <p x-show="results.total_resultados === 0 && !loading" class="text-sm text-slate-500 text-center py-8">
          Nenhum resultado encontrado.
        </p>
      </div>
    </div>
  `;
}

function consultaPage() {
  return {
    query: "",
    results: {},
    loading: false,
    searched: false,
    _timer: null,

    onInput() {
      clearTimeout(this._timer);
      if (this.query.length < 2) {
        this.results = {};
        this.searched = false;
        return;
      }
      this._timer = setTimeout(() => this.search(), 400);
    },

    async search() {
      this.loading = true;
      try {
        this.results = await api.get(`/consultas/?q=${encodeURIComponent(this.query)}`);
        this.searched = true;
      } catch {
        showToast("Erro na busca", "error");
      } finally {
        this.loading = false;
      }
    },

    viewPessoa(id) {
      // Navegar para detalhe via app
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0].currentPage = "pessoa-detalhe";
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },
  };
}
