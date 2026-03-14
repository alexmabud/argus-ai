/**
 * Página de dashboard analítico — Argus AI.
 *
 * Cards de resumo por período (hoje/mês/total), gráficos de linha ApexCharts
 * (por dia e por mês), calendário interativo com pessoas do dia escolhido,
 * e top 10 pessoas recorrentes.
 */
function renderDashboard() {
  return `
    <div x-data="dashboardPage()" x-init="load()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Dashboard</h2>

      <!-- Loading -->
      <div x-show="loading" class="flex justify-center py-12">
        <span class="spinner"></span>
      </div>

      <template x-if="!loading">
        <div class="space-y-5">

          <!-- === SEÇÃO 1: Cards de Resumo === -->
          <!-- Card: Hoje -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Hoje</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="hoje.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="hoje.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- Card: Este Mês -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Este Mês</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="mes.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="mes.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- Card: Total -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Total</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="total.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="total.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- === SEÇÃO 2: Gráficos === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Abordagens por Dia (últimos 30 dias)</h3>
            <div id="chart-por-dia"></div>
          </div>

          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Abordagens por Mês (últimos 12 meses)</h3>
            <div id="chart-por-mes"></div>
          </div>

          <!-- === SEÇÃO 3: Calendário + Pessoas do Dia === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Pessoas Abordadas por Dia</h3>

            <!-- Navegação do calendário -->
            <div class="flex items-center justify-between mb-3">
              <button @click="mesMenos()" class="text-slate-400 hover:text-slate-200 px-2 py-1 text-lg">&#8249;</button>
              <span class="text-sm font-medium text-slate-200" x-text="mesAtualLabel"></span>
              <button @click="mesMais()" class="text-slate-400 hover:text-slate-200 px-2 py-1 text-lg">&#8250;</button>
            </div>

            <!-- Header dias da semana -->
            <div class="grid grid-cols-7 gap-1 text-center mb-1">
              <span class="text-[10px] text-slate-500 font-medium">D</span>
              <span class="text-[10px] text-slate-500 font-medium">S</span>
              <span class="text-[10px] text-slate-500 font-medium">T</span>
              <span class="text-[10px] text-slate-500 font-medium">Q</span>
              <span class="text-[10px] text-slate-500 font-medium">Q</span>
              <span class="text-[10px] text-slate-500 font-medium">S</span>
              <span class="text-[10px] text-slate-500 font-medium">S</span>
            </div>

            <!-- Grid de dias -->
            <div class="grid grid-cols-7 gap-1 text-center mb-4">
              <!-- Células vazias antes do dia 1 -->
              <template x-for="v in primeiroDiaSemana" :key="'v' + v">
                <div></div>
              </template>
              <!-- Dias do mês -->
              <template x-for="dia in diasDoMes" :key="dia">
                <button
                  class="relative text-xs py-1 rounded flex flex-col items-center"
                  :class="isDiaSelecionado(dia) ? 'bg-blue-600 text-white font-bold' : 'text-slate-300 hover:bg-slate-700'"
                  @click="selecionarDia(dia)">
                  <span x-text="dia"></span>
                  <span
                    x-show="diaTemAbordagem(dia)"
                    class="w-1 h-1 rounded-full bg-blue-400 mt-0.5">
                  </span>
                </button>
              </template>
            </div>

            <!-- Loading pessoas do dia -->
            <div x-show="loadingPessoas" class="flex justify-center py-4">
              <span class="spinner"></span>
            </div>

            <!-- Lista de pessoas do dia -->
            <div x-show="!loadingPessoas">
              <div x-show="pessoasDoDia.length === 0" class="text-xs text-slate-500 text-center py-4">
                Nenhuma abordagem neste dia.
              </div>
              <div class="space-y-2">
                <template x-for="p in pessoasDoDia" :key="p.id">
                  <div
                    class="flex items-center gap-3 cursor-pointer hover:bg-slate-700 rounded p-1 -mx-1"
                    @click="navigate('pessoa-detalhe', { id: p.id })">
                    <img
                      :src="p.foto_url || '/icons/icon-192.png'"
                      class="w-8 h-8 rounded-full object-cover flex-shrink-0 bg-slate-700"
                      :alt="p.nome">
                    <div class="min-w-0">
                      <p class="text-sm text-slate-200 truncate" x-text="p.nome"></p>
                      <p class="text-xs text-slate-400" x-text="p.cpf || '—'"></p>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- === SEÇÃO 4: Pessoas Recorrentes === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Pessoas Recorrentes</h3>
            <div x-show="recorrentes.length === 0" class="text-xs text-slate-500 text-center py-4">
              Nenhum dado disponível.
            </div>
            <div class="space-y-2">
              <template x-for="(p, i) in recorrentes" :key="p.id">
                <div
                  class="flex items-center gap-3 cursor-pointer hover:bg-slate-700 rounded p-1 -mx-1"
                  @click="navigate('pessoa-detalhe', { id: p.id })">
                  <span class="text-xs text-slate-500 w-5 flex-shrink-0" x-text="(i+1) + '.'"></span>
                  <img
                    :src="p.foto_url || '/icons/icon-192.png'"
                    class="w-8 h-8 rounded-full object-cover flex-shrink-0 bg-slate-700"
                    :alt="p.nome">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-slate-200 truncate" x-text="p.nome"></p>
                    <p class="text-xs text-slate-400" x-text="p.cpf || '—'"></p>
                  </div>
                  <span class="text-blue-400 font-bold text-sm flex-shrink-0" x-text="p.total_abordagens + 'x'"></span>
                </div>
              </template>
            </div>
          </div>

        </div>
      </template>
    </div>
  `;
}

function dashboardPage() {
  const agora = new Date();
  return {
    loading: true,
    loadingPessoas: false,

    // Resumos
    hoje: {},
    mes: {},
    total: {},

    // Gráficos
    porDia: [],
    porMes: [],

    // Calendário
    anoCalendarioAtual: agora.getFullYear(),
    mesCalendarioAtual: agora.getMonth() + 1,
    anoHoje: agora.getFullYear(),
    mesHoje: agora.getMonth() + 1,
    diaHoje: agora.getDate(),
    diaSelecionado: agora.getDate(),
    _anoSelec: agora.getFullYear(),
    _mesSelec: agora.getMonth() + 1,
    diasComAbordagem: [],
    pessoasDoDia: [],

    // Recorrentes
    recorrentes: [],

    get mesAtualLabel() {
      const meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                     'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
      return `${meses[this.mesCalendarioAtual - 1]} ${this.anoCalendarioAtual}`;
    },

    get primeiroDiaSemana() {
      const d = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual - 1, 1);
      return Array.from({ length: d.getDay() }, (_, i) => i);
    },

    get diasDoMes() {
      const total = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual, 0).getDate();
      return Array.from({ length: total }, (_, i) => i + 1);
    },

    diaTemAbordagem(dia) {
      return this.diasComAbordagem.includes(dia);
    },

    isDiaSelecionado(dia) {
      return (
        this.diaSelecionado === dia &&
        this._mesSelec === this.mesCalendarioAtual &&
        this._anoSelec === this.anoCalendarioAtual
      );
    },

    async mesMenos() {
      if (this.mesCalendarioAtual === 1) {
        this.mesCalendarioAtual = 12;
        this.anoCalendarioAtual--;
      } else {
        this.mesCalendarioAtual--;
      }
      this.diaSelecionado = null;
      await this.carregarDiasComAbordagem();
    },

    async mesMais() {
      if (this.mesCalendarioAtual === 12) {
        this.mesCalendarioAtual = 1;
        this.anoCalendarioAtual++;
      } else {
        this.mesCalendarioAtual++;
      }
      this.diaSelecionado = null;
      await this.carregarDiasComAbordagem();
    },

    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      await this.carregarPessoasDoDia(dataStr);
    },

    async carregarDiasComAbordagem() {
      const mes = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;
      this.diasComAbordagem = await api.get(`/analytics/dias-com-abordagem?mes=${mes}`).catch(() => []);
    },

    async carregarPessoasDoDia(data) {
      this.loadingPessoas = true;
      try {
        this.pessoasDoDia = await api.get(`/analytics/pessoas-do-dia?data=${data}`).catch(() => []);
      } finally {
        this.loadingPessoas = false;
      }
    },

    renderizarGraficoPorDia() {
      const el = document.querySelector('#chart-por-dia');
      if (!el || !this.porDia.length) return;
      const categorias = this.porDia.map(d => {
        const [, m, dia] = d.data.split('-');
        return `${dia}/${m}`;
      });
      new ApexCharts(el, {
        chart: { type: 'line', height: 180, background: 'transparent', toolbar: { show: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: this.porDia.map(d => d.abordagens), color: '#60a5fa' },
          { name: 'Pessoas', data: this.porDia.map(d => d.pessoas), color: '#4ade80' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '9px' }, rotate: -45 } },
        yaxis: { labels: { style: { fontSize: '10px' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#94a3b8' } },
        grid: { borderColor: '#334155' },
        tooltip: { theme: 'dark' },
      }).render();
    },

    renderizarGraficoPorMes() {
      const el = document.querySelector('#chart-por-mes');
      if (!el || !this.porMes.length) return;
      const nomesMes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
      const categorias = this.porMes.map(d => {
        const [ano, m] = d.mes.split('-');
        return `${nomesMes[parseInt(m) - 1]}/${ano.slice(2)}`;
      });
      new ApexCharts(el, {
        chart: { type: 'line', height: 180, background: 'transparent', toolbar: { show: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: this.porMes.map(d => d.abordagens), color: '#60a5fa' },
          { name: 'Pessoas', data: this.porMes.map(d => d.pessoas), color: '#4ade80' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '10px' } } },
        yaxis: { labels: { style: { fontSize: '10px' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#94a3b8' } },
        grid: { borderColor: '#334155' },
        tooltip: { theme: 'dark' },
      }).render();
    },

    async load() {
      try {
        const dataHoje = `${this.anoHoje}-${String(this.mesHoje).padStart(2,'0')}-${String(this.diaHoje).padStart(2,'0')}`;
        const mesAtual = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;

        const [resumoHoje, resumoMes, resumoTotal, porDia, porMes, diasAbordagem, pessoasHoje, recorrentes] =
          await Promise.all([
            api.get('/analytics/resumo-hoje').catch(() => ({})),
            api.get('/analytics/resumo-mes').catch(() => ({})),
            api.get('/analytics/resumo-total').catch(() => ({})),
            api.get('/analytics/por-dia?dias=30').catch(() => []),
            api.get('/analytics/por-mes?meses=12').catch(() => []),
            api.get(`/analytics/dias-com-abordagem?mes=${mesAtual}`).catch(() => []),
            api.get(`/analytics/pessoas-do-dia?data=${dataHoje}`).catch(() => []),
            api.get('/analytics/pessoas-recorrentes?limit=10').catch(() => []),
          ]);

        this.hoje = resumoHoje;
        this.mes = resumoMes;
        this.total = resumoTotal;
        this.porDia = porDia;
        this.porMes = porMes;
        this.diasComAbordagem = diasAbordagem;
        this.pessoasDoDia = pessoasHoje;
        this.recorrentes = recorrentes;
      } catch {
        showToast('Erro ao carregar dashboard', 'error');
      } finally {
        this.loading = false;
        await this.$nextTick();
        this.renderizarGraficoPorDia();
        this.renderizarGraficoPorMes();
      }
    },
  };
}
