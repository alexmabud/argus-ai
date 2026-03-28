/**
 * Pagina de dashboard analitico — Argus AI.
 *
 * Cards de resumo por periodo (hoje/mes/total), graficos de linha ApexCharts
 * (por dia e por mes), calendario interativo com pessoas do dia escolhido,
 * e top 10 pessoas recorrentes. Estetica cyberpunk tatica.
 */
function renderDashboard() {
  return `
    <style>
      .cal-day {
        position: relative;
        font-family: var(--font-data);
        font-size: 11px;
        font-weight: 500;
        height: 30px;
        border-radius: 4px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border: 1px solid transparent;
        background: transparent;
        transition: background 150ms, border-color 150ms, color 150ms;
        color: var(--color-text-muted);
        width: 100%;
      }
      .cal-day:hover {
        background: rgba(0, 212, 255, 0.06);
        border-color: rgba(0, 212, 255, 0.2);
        color: var(--color-text);
      }
      .cal-day.is-selecionado {
        background: rgba(0, 212, 255, 0.15);
        border-color: rgba(0, 212, 255, 0.4);
        color: var(--color-primary);
        font-weight: 700;
        box-shadow: 0 0 8px rgba(0, 212, 255, 0.15);
      }
      .cal-day.is-selecionado:hover {
        background: rgba(0, 212, 255, 0.2);
      }
      .cal-day.is-hoje .cal-day-num {
        color: var(--color-primary);
        text-decoration: underline;
        text-underline-offset: 3px;
      }
      .cal-led {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: var(--color-primary);
        box-shadow: 0 0 5px var(--color-primary);
        margin-top: 2px;
        flex-shrink: 0;
      }
    </style>
    <div x-data="dashboardPage()" x-init="load()" style="display:flex;flex-direction:column;gap:20px;">

      <!-- Header da pagina -->
      <div>
        <h2 style="font-family: var(--font-display); font-size: 18px; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.08em;">
          Analitico
        </h2>
        <p style="font-family: var(--font-data); font-size: 12px; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px;">
          Metricas Operacionais
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
                <span style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;">Este Mes</span>
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
              Abordagens por Mes
              <span style="color:var(--color-text-dim);font-weight:400;"> // 12 meses</span>
            </h3>
            <div id="chart-por-mes"></div>
          </div>

          <!-- Calendario + Pessoas do Dia -->
          <div class="glass-card" style="padding:16px;border-radius:4px;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
              Pessoas Abordadas por Dia
            </h3>

            <!-- Navegacao do calendario -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
              <button @click="mesMenos()"
                      style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                      onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.color='var(--color-primary)'"
                      onmouseout="this.style.borderColor='var(--color-border)';this.style.color='var(--color-text-muted)'"
              >&#8249;</button>
              <span style="font-family:var(--font-data);font-size:14px;font-weight:600;color:var(--color-text);" x-text="mesAtualLabel"></span>
              <button @click="mesMais()"
                      style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                      onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.color='var(--color-primary)'"
                      onmouseout="this.style.borderColor='var(--color-border)';this.style.color='var(--color-text-muted)'"
              >&#8250;</button>
            </div>

            <!-- Header dias da semana -->
            <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;margin-bottom:2px;">
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">D</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">T</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">Q</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">Q</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
              <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
            </div>

            <!-- Grid de dias -->
            <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;margin-bottom:12px;">
              <template x-for="v in primeiroDiaSemana" :key="'v' + v">
                <div></div>
              </template>
              <template x-for="dia in diasDoMes" :key="dia">
                <button
                  class="cal-day"
                  :class="{
                    'is-selecionado': isDiaSelecionado(dia),
                    'is-hoje': diaEHoje(dia)
                  }"
                  @click="selecionarDia(dia)">
                  <span class="cal-day-num" x-text="dia"></span>
                  <span class="cal-led" x-show="diaTemAbordagem(dia)"></span>
                </button>
              </template>
            </div>

            <!-- Loading pessoas do dia -->
            <div x-show="loadingPessoas" style="display:flex;justify-content:center;padding:16px 0;">
              <span class="spinner"></span>
            </div>

            <!-- Lista de pessoas do dia -->
            <div x-show="!loadingPessoas">
              <div x-show="pessoasDoDia.length === 0"
                   style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
                Nenhuma abordagem neste dia.
              </div>
              <div style="display:flex;flex-direction:column;gap:4px;">
                <template x-for="p in pessoasDoDia" :key="p.id">
                  <div @click="viewPessoa(p.id)"
                       style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:4px;cursor:pointer;border:1px solid transparent;transition:all 150ms;"
                       onmouseover="this.style.background='var(--color-surface-hover)';this.style.borderColor='rgba(0,212,255,0.15)'"
                       onmouseout="this.style.background='transparent';this.style.borderColor='transparent'">
                    <img :src="p.foto_url || '/icons/icon-192.png'"
                         style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);"
                         :alt="p.nome">
                    <div style="min-width:0;flex:1;">
                      <p style="font-family:var(--font-body);font-size:13px;color:var(--color-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="p.nome"></p>
                      <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="p.cpf || '\u2014'"></p>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Pessoas Recorrentes -->
          <div class="glass-card" style="padding:16px;border-radius:4px;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
              Pessoas Recorrentes
              <span style="color:var(--color-text-dim);font-weight:400;"> // Top 10</span>
            </h3>
            <div x-show="recorrentes.length === 0"
                 style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
              Nenhum dado disponivel.
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;">
              <template x-for="(p, i) in recorrentes" :key="p.id">
                <div @click="viewPessoa(p.id)"
                     style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:4px;cursor:pointer;border:1px solid transparent;transition:all 150ms;"
                     onmouseover="this.style.background='var(--color-surface-hover)';this.style.borderColor='rgba(0,212,255,0.15)'"
                     onmouseout="this.style.background='transparent';this.style.borderColor='transparent'">
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
    </div>
  `;
}

/**
 * Componente Alpine.js do dashboard analitico.
 *
 * Gerencia estado de resumos, graficos, calendario e pessoas recorrentes.
 * Carrega dados via API e renderiza graficos ApexCharts com tema tatico.
 */
function dashboardPage() {
  const agora = new Date();
  return {
    loading: true,
    loadingPessoas: false,

    // Resumos
    hoje: {},
    mes: {},
    total: {},

    // Graficos
    porDia: [],
    porMes: [],

    // Calendario
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

    // Mapa do dia
    pontosMapaDia: [],
    mapaAnaliticoInst: null,
    _mapaAnaliticoObserver: null,
    modoMapaAnalitico: 'marcadores',
    clusterAnalitico: null,
    heatAnalitico: null,

    // Recorrentes
    recorrentes: [],

    get mesAtualLabel() {
      const meses = ['Janeiro','Fevereiro','Mar\u00e7o','Abril','Maio','Junho',
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

    diaEHoje(dia) {
      return (
        dia === this.diaHoje &&
        this.mesCalendarioAtual === this.mesHoje &&
        this.anoCalendarioAtual === this.anoHoje
      );
    },

    async mesMenos() {
      if (this.mesCalendarioAtual === 1) {
        this.mesCalendarioAtual = 12;
        this.anoCalendarioAtual--;
      } else {
        this.mesCalendarioAtual--;
      }
      this.destroyMapaAnalitico();
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
      this.destroyMapaAnalitico();
      this.diaSelecionado = null;
      await this.carregarDiasComAbordagem();
    },

    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      this.destroyMapaAnalitico();
      await Promise.all([
        this.carregarPessoasDoDia(dataStr),
        this.carregarPontosMapaDia(dataStr),
      ]);
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

    async carregarPontosMapaDia(data) {
      this.pontosMapaDia = await api.get(`/analytics/abordagens-do-dia?data=${data}`).catch(() => []);
      if (this.pontosMapaDia.length > 0) {
        await this.$nextTick();
        await this.setupMapaAnaliticoObserver();
      }
    },

    async setupMapaAnaliticoObserver() {
      if (this._mapaAnaliticoObserver) {
        this._mapaAnaliticoObserver.disconnect();
        this._mapaAnaliticoObserver = null;
      }
      await new Promise(r => setTimeout(r, 0));
      const div = document.getElementById('mapa-analitico-dia');
      if (!div) return;
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          this.initMapaAnalitico();
        }
      }, { threshold: 0.1 });
      observer.observe(div);
      this._mapaAnaliticoObserver = observer;
    },

    initMapaAnalitico() {
      const div = document.getElementById('mapa-analitico-dia');
      if (!div || this.mapaAnaliticoInst) return;
      if (typeof L === 'undefined') return;

      this.mapaAnaliticoInst = L.map(div, { zoomControl: true });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(this.mapaAnaliticoInst);

      const pontos = this.pontosMapaDia;

      this.clusterAnalitico = L.markerClusterGroup();
      pontos.forEach(p => {
        const marker = L.marker([p.lat, p.lng]);
        const popupEl = document.createElement('span');
        popupEl.style.cssText = 'font-family:monospace;font-size:12px;';
        popupEl.textContent = p.horario;
        marker.bindPopup(popupEl);
        this.clusterAnalitico.addLayer(marker);
      });

      const heatPontos = pontos.map(p => [p.lat, p.lng, 1]);
      this.heatAnalitico = L.heatLayer(heatPontos, { radius: 30, blur: 20, maxZoom: 17 });

      this.mapaAnaliticoInst.addLayer(this.clusterAnalitico);

      if (pontos.length === 1) {
        this.mapaAnaliticoInst.setView([pontos[0].lat, pontos[0].lng], 15);
      } else {
        const bounds = L.latLngBounds(pontos.map(p => [p.lat, p.lng]));
        this.mapaAnaliticoInst.fitBounds(bounds, { padding: [30, 30] });
      }

      requestAnimationFrame(() => {
        this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false });
        setTimeout(() => this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false }), 200);
        setTimeout(() => this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false }), 500);
      });
    },

    toggleModoMapaAnalitico(modo) {
      if (!this.mapaAnaliticoInst || modo === this.modoMapaAnalitico) return;
      this.modoMapaAnalitico = modo;
      if (modo === 'marcadores') {
        this.mapaAnaliticoInst.removeLayer(this.heatAnalitico);
        this.mapaAnaliticoInst.addLayer(this.clusterAnalitico);
      } else {
        this.mapaAnaliticoInst.removeLayer(this.clusterAnalitico);
        this.mapaAnaliticoInst.addLayer(this.heatAnalitico);
      }
    },

    destroyMapaAnalitico() {
      if (this._mapaAnaliticoObserver) {
        this._mapaAnaliticoObserver.disconnect();
        this._mapaAnaliticoObserver = null;
      }
      if (this.mapaAnaliticoInst) {
        this.mapaAnaliticoInst.remove();
        this.mapaAnaliticoInst = null;
        this.clusterAnalitico = null;
        this.heatAnalitico = null;
      }
      this.pontosMapaDia = [];
      this.modoMapaAnalitico = 'marcadores';
    },

    /**
     * Renderiza grafico de abordagens por dia com tema tatico.
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
     * Renderiza grafico de abordagens por mes com tema tatico.
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
