/**
 * Página de dashboard analítico — Argus AI.
 *
 * Cards de resumo por período (hoje/mês/total), gráficos de linha ApexCharts
 * (por dia e por mês), calendário interativo com pessoas do dia escolhido,
 * e top 10 pessoas recorrentes. Estética cyberpunk tática.
 */
function renderDashboard() {
  return `
    <div x-data="dashboardPage()" x-init="load()" style="display:flex;flex-direction:column;gap:20px;">

      <!-- Header da página -->
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <h2 style="font-family: var(--font-display); font-size: 18px; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.08em;">
            Analítico
          </h2>
          <p style="font-family: var(--font-data); font-size: 12px; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px;">
            Métricas Operacionais
          </p>
        </div>
        <p x-show="!loading" style="font-family: var(--font-data); font-size: 12px; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; white-space: nowrap;">
          Pessoas Cadastradas:
          <span x-text="(total.pessoas_cadastradas ?? 0).toLocaleString('pt-BR')"
                style="color: var(--color-success); font-size: 14px; font-weight: 700; text-shadow: 0 0 8px rgba(0,255,136,0.7), 0 0 20px rgba(0,255,136,0.35);"></span>
        </p>
      </div>

      <!-- Loading -->
      <div x-show="loading" style="display:flex;justify-content:center;padding:48px 0;">
        <div style="text-align:center;">
          <span class="spinner spinner-lg"></span>
          <p style="font-family: var(--font-data); font-size: 11px; color: var(--color-text-dim); margin-top: 12px; text-transform: uppercase; letter-spacing: 0.1em;">
            Carregando dados...
          </p>
        </div>
      </div>

      <template x-if="!loading">
        <div style="display:flex;flex-direction:column;gap:20px;">

          <!-- Cards de Resumo — grid 3 colunas desktop -->
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:12px;">

            <!-- Hoje -->
            <div class="glass-card" style="padding:16px;border-radius:4px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;">Hoje</span>
                <span class="status-dot status-dot-online"></span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-primary);line-height:1;" x-text="hoje.abordagens ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Abordagens</p>
                </div>
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-success);line-height:1;" x-text="hoje.pessoas ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Pessoas</p>
                </div>
              </div>
            </div>

            <!-- Este Mes -->
            <div class="glass-card" style="padding:16px;border-radius:4px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;">Este Mês</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-dim)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-primary);line-height:1;" x-text="mes.abordagens ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Abordagens</p>
                </div>
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-success);line-height:1;" x-text="mes.pessoas ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Pessoas</p>
                </div>
              </div>
            </div>

            <!-- Total -->
            <div class="glass-card" style="padding:16px;border-radius:4px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;">Total</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-dim)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-primary);line-height:1;" x-text="total.abordagens ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Abordagens</p>
                </div>
                <div>
                  <p style="font-family:var(--font-data);font-size:28px;font-weight:700;color:var(--color-success);line-height:1;" x-text="total.pessoas ?? 0"></p>
                  <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Pessoas</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Graficos -->
          <div class="glass-card" style="padding:16px;border-radius:4px;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
              Abordagens por Dia
              <span style="color:var(--color-text-dim);font-weight:400;"> // 30 dias</span>
            </h3>
            <div id="chart-por-dia"></div>
          </div>

          <div class="glass-card" style="padding:16px;border-radius:4px;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
              Abordagens por Mês
              <span style="color:var(--color-text-dim);font-weight:400;"> // 12 meses</span>
            </h3>
            <div id="chart-por-mes"></div>
          </div>

          <!-- Pessoas Recorrentes -->
          <div class="glass-card" style="padding:16px;border-radius:4px;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
              Pessoas Recorrentes
              <span style="color:var(--color-text-dim);font-weight:400;"> // Top 10</span>
            </h3>
            <div x-show="recorrentes.length === 0"
                 style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
              Nenhum dado disponível.
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;">
              <template x-for="(p, i) in recorrentes" :key="p.id">
                <div @click="if(p.foto_url) openPhotoModal(p.foto_url, p.id, p); else viewPessoa(p.id)"
                     style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:4px;cursor:pointer;border:1px solid transparent;transition:all 150ms;"
                     class="hov-dash-card">
                  <!-- Rank badge -->
                  <span style="font-family:var(--font-data);font-size:12px;font-weight:700;color:var(--color-primary);width:20px;flex-shrink:0;text-align:center;"
                        x-text="(i+1)"></span>
                  <img :src="p.foto_url || '/icons/icon-192.png'"
                       style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);"
                       :alt="p.nome">
                  <div style="flex:1;min-width:0;">
                    <p style="font-family:var(--font-body);font-size:13px;color:var(--color-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="p.nome"></p>
                    <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="p.cpf || '\u2014'"></p>
                  </div>
                  <!-- Contagem -->
                  <span style="font-family:var(--font-data);font-size:14px;font-weight:700;color:var(--color-primary);flex-shrink:0;"
                        x-text="p.total_abordagens + 'x'"></span>
                </div>
              </template>
            </div>
          </div>

        </div>
      </template>

      ${personPhotoModalHTML()}
    </div>
  `;
}

/**
 * Componente Alpine.js do dashboard analítico.
 *
 * Gerencia estado de resumos, gráficos, calendário e pessoas recorrentes.
 * Carrega dados via API e renderiza gráficos ApexCharts com tema tático.
 */
function dashboardPage() {
  return {
    // personPhotoModal() só tem dados/métodos (sem getters), então pode ser
    // mesclado diretamente aqui.
    ...personPhotoModal(),

    loading: true,

    // Resumos
    hoje: {},
    mes: {},
    total: {},

    // Graficos
    porDia: [],
    porMes: [],

    // Recorrentes
    recorrentes: [],

    /**
     * Renderiza gráfico de abordagens por dia com tema tático.
     */
    renderizarGraficoPorDia() {
      const el = document.querySelector('#chart-por-dia');
      if (!el || !this.porDia.length || !el.offsetWidth) return;
      const categorias = this.porDia.map(d => {
        const [, m, dia] = d.data.split('-');
        return `${dia}/${m}`;
      });
      this._chartDia = new ApexCharts(el, {
        chart: { type: 'line', height: 180, width: el.offsetWidth, background: 'transparent',
          toolbar: { show: false }, fontFamily: 'Rajdhani, sans-serif',
          animations: { enabled: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: this.porDia.map(d => d.abordagens), color: '#00D4FF' },
          { name: 'Pessoas', data: this.porDia.map(d => d.pessoas), color: '#00FF88' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '9px', colors: '#6B8FA8' }, rotate: -45 } },
        yaxis: { labels: { style: { fontSize: '10px', colors: '#6B8FA8' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#6B8FA8' }, fontFamily: 'Rajdhani, sans-serif' },
        grid: { borderColor: '#1A2940' },
        tooltip: { theme: 'dark',
          style: { fontFamily: 'IBM Plex Sans, sans-serif' } },
      });
      this._chartDia.render();
    },

    /**
     * Renderiza gráfico de abordagens por mês com tema tático.
     */
    renderizarGraficoPorMes() {
      const el = document.querySelector('#chart-por-mes');
      if (!el || !this.porMes.length || !el.offsetWidth) return;
      const nomesMes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
      const categorias = this.porMes.map(d => {
        const [ano, m] = d.mes.split('-');
        return `${nomesMes[parseInt(m) - 1]}/${ano.slice(2)}`;
      });
      this._chartMes = new ApexCharts(el, {
        chart: { type: 'line', height: 180, width: el.offsetWidth, background: 'transparent',
          toolbar: { show: false }, fontFamily: 'Rajdhani, sans-serif',
          animations: { enabled: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: this.porMes.map(d => d.abordagens), color: '#00D4FF' },
          { name: 'Pessoas', data: this.porMes.map(d => d.pessoas), color: '#00FF88' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '10px', colors: '#6B8FA8' } } },
        yaxis: { labels: { style: { fontSize: '10px', colors: '#6B8FA8' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#6B8FA8' }, fontFamily: 'Rajdhani, sans-serif' },
        grid: { borderColor: '#1A2940' },
        tooltip: { theme: 'dark',
          style: { fontFamily: 'IBM Plex Sans, sans-serif' } },
      });
      this._chartMes.render();
    },

    /**
     * Carrega todos os dados do dashboard via API.
     */
    async load() {
      try {
        const [resumoHoje, resumoMes, resumoTotal, porDia, porMes, recorrentes] =
          await Promise.all([
            api.get('/analytics/resumo-hoje').catch(() => ({})),
            api.get('/analytics/resumo-mes').catch(() => ({})),
            api.get('/analytics/resumo-total').catch(() => ({})),
            api.get('/analytics/por-dia?dias=30').catch(() => []),
            api.get('/analytics/por-mes?meses=12').catch(() => []),
            api.get('/analytics/pessoas-recorrentes?limit=10').catch(() => []),
          ]);

        this.hoje = resumoHoje;
        this.mes = resumoMes;
        this.total = resumoTotal;
        this.porDia = porDia;
        this.porMes = porMes;
        this.recorrentes = recorrentes;
      } catch {
        showToast('Erro ao carregar dashboard', 'error');
      } finally {
        this.loading = false;
        await this.$nextTick();
        // Aguarda o browser calcular layout do DOM. x-if insere elementos
        // no nextTick, mas dimensões computadas só existem após o primeiro
        // paint. Dois requestAnimationFrame garantem: 1º = elementos
        // inseridos, 2º = layout calculado com larguras reais.
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            this.renderizarGraficoPorDia();
            this.renderizarGraficoPorMes();
          });
        });
      }
    },

    /**
     * Navega para a ficha de uma pessoa.
     */
    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].navigate("pessoa-detalhe");
      }
    },
  };
}
