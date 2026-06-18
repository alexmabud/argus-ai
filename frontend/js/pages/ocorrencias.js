/**
 * Página de Relatório de Abordagens — Argus AI.
 *
 * Exibe calendário interativo com dias que tiveram abordagens e,
 * ao selecionar um dia, lista os cards completos das abordagens do dia.
 * Layout e componente de calendário idênticos à página Analítico.
 */

function renderOcorrencias() {
  return `
    <div x-data="ocorrenciasPage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.1em;margin:0;">
          RELATÓRIO DE ABORDAGENS
        </h2>
      </div>

      <!-- Busca local -->
      <div style="display:flex;align-items:center;gap:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 12px;">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="search" x-model="filtro" @input="onFiltroInput()" placeholder="Buscar por nome, placa, veículo, endereço em todas as datas..."
          style="background:none;border:none;outline:none;color:var(--color-text);font-family:var(--font-data);font-size:13px;width:100%;">
      </div>

      <!-- Contagem do conjunto exibido -->
      <div class="glass-card" style="padding:10px 16px;border-radius:4px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
          <span style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;" x-text="labelContagem"></span>
          <span class="status-dot status-dot-online"></span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
          <div>
            <p style="font-family:var(--font-data);font-size:22px;font-weight:700;color:var(--color-primary);line-height:1;" x-text="total"></p>
            <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Abordagens</p>
          </div>
          <div>
            <p style="font-family:var(--font-data);font-size:22px;font-weight:700;color:var(--color-success);line-height:1;" x-text="totalPessoas"></p>
            <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Pessoas</p>
          </div>
        </div>
      </div>

      <!-- Calendário -->
      <div class="glass-card" style="padding:16px;border-radius:4px;">
        <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
          Abordagens por Dia
        </h3>

        <!-- Navegação do mês -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <button @click="mesMenos()"
                  style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                  class="hov-tab-pill"
          >&#8249;</button>
          <span style="font-family:var(--font-data);font-size:14px;font-weight:600;color:var(--color-text);" x-text="mesAtualLabel"></span>
          <button @click="mesMais()"
                  style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                  class="hov-tab-pill"
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
        <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;">
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
      </div>

      <!-- Mapa de localização -->
      <div x-show="!loading && (diaSelecionado || filtro)"
           class="glass-card"
           style="padding:16px;border-radius:4px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin:0;">
            Localização das Abordagens
          </h3>
          <div x-show="pontosMapa.length > 0" style="display:flex;gap:0.25rem;">
            <button
              @click="toggleModoMapaAnalitico('marcadores')"
              style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:4px;border:none;cursor:pointer;transition:all 0.2s;"
              :style="modoMapaAnalitico === 'marcadores' ? 'background:#14B8A6;color:var(--color-bg);' : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'"
            >Marcadores</button>
            <button
              @click="toggleModoMapaAnalitico('calor')"
              style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:4px;border:none;cursor:pointer;transition:all 0.2s;"
              :style="modoMapaAnalitico === 'calor' ? 'background:#14B8A6;color:var(--color-bg);' : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'"
            >Calor</button>
          </div>
        </div>

        <div x-show="pontosMapa.length === 0"
             style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
          Sem dados de localização.
        </div>

        <div x-show="pontosMapa.length > 0">
          <div id="mapa-relatorio-dia"
               style="width:100%;height:280px;border-radius:4px;background:var(--color-surface);z-index:1;"></div>
        </div>
      </div>

      <!-- Loading -->
      <div x-show="loading" style="text-align:center;padding:32px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-danger);" x-text="erro"></p>
        <button @click="selecionarDia(diaSelecionado)" class="btn btn-secondary" style="margin-top:8px;width:auto;padding:6px 16px;">Tentar novamente</button>
      </div>

      <!-- Vazio -->
      <div x-show="!loading && !erro && (diaSelecionado || filtro) && abordagensFiltradas.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
        <span x-show="filtro">Nenhum resultado para "<span x-text="filtro"></span>"</span>
        <span x-show="!filtro">Nenhuma abordagem neste dia.</span>
      </div>

      <!-- Lista de abordagens do dia -->
      <template x-for="ab in abordagensFiltradas" :key="ab.id">
        <div class="glass-card" :class="ab.ocorrencias && ab.ocorrencias.length ? 'card-led-blue' : ''"
             style="padding:12px;cursor:pointer;border-radius:4px;"
             @click="abrirDetalhe(ab.id)">

          <!-- Row principal -->
          <div style="display:flex;align-items:center;gap:10px;">
            <!-- Avatares -->
            <div style="display:flex;">
              <template x-for="(p, i) in ab.pessoas.slice(0, 3)" :key="p.id">
                <div :style="'width:36px;height:36px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:11px;font-weight:700;color:var(--color-primary);flex-shrink:0;' + (i > 0 ? 'margin-left:-8px;' : '') + (p.foto_principal_url ? 'padding:0;overflow:hidden;' : '')">
                  <template x-if="p.foto_principal_url">
                    <img :src="p.foto_principal_thumb_url || p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                  </template>
                  <template x-if="!p.foto_principal_url">
                    <span x-text="iniciais(p.nome)"></span>
                  </template>
                </div>
              </template>
              <template x-if="ab.pessoas.length === 0">
                <div style="width:36px;height:36px;border-radius:4px;border:1px dashed var(--color-border);display:flex;align-items:center;justify-content:center;">
                  <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
              </template>
            </div>

            <!-- Info -->
            <div style="flex:1;min-width:0;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
                      x-text="formatarDataHora(ab.data_hora)"></span>
                <span x-show="ab.usuario && ab.usuario.nome_guerra"
                      style="font-family:var(--font-display);font-size:10px;color:rgba(255,255,255,0.45);letter-spacing:0.06em;"
                      x-text="(ab.usuario && ab.usuario.posto_graduacao ? (POSTO_ABREV[ab.usuario.posto_graduacao] || ab.usuario.posto_graduacao) + ' ' : '') + (ab.usuario && ab.usuario.nome_guerra ? ab.usuario.nome_guerra : '')"></span>
              </div>
              <div style="font-family:var(--font-data);font-size:13px;font-weight:600;color:var(--color-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="nomesPessoas(ab.pessoas) || 'Sem abordados registrados'"></div>
              <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="ab.endereco_texto || 'Endereço não disponível'"></div>
            </div>
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;"><path d="M9 18l6-6-6-6"/></svg>
          </div>

          <!-- Footer badges -->
          <div style="display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap;">
            <span style="font-family:var(--font-data);font-size:9px;padding:2px 6px;border-radius:2px;background:rgba(0,212,255,0.06);color:var(--color-text-dim);border:1px solid var(--color-border);"
                  x-text="'#' + ab.id"></span>
            <template x-if="ab.ocorrencias && ab.ocorrencias.length > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);">RAP vinculada</span>
            </template>
            <template x-if="!ab.ocorrencias || !ab.ocorrencias.length">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(255,107,0,0.1);color:var(--color-danger);border:1px solid rgba(255,107,0,0.25);">Sem RAP</span>
            </template>
            <template x-if="midias(ab.fotos) > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,212,255,0.08);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);"
                    x-text="midias(ab.fotos) + ' mídia' + (midias(ab.fotos) > 1 ? 's' : '')"></span>
            </template>
            <template x-if="ab.veiculos && ab.veiculos.length > 0">
              <span style="margin-left:auto;font-family:var(--font-display);font-size:9px;color:var(--color-text-dim);background:var(--color-surface);border:1px solid var(--color-border);border-radius:2px;padding:1px 5px;"
                    x-text="ab.veiculos.length + ' veículo' + (ab.veiculos.length > 1 ? 's' : '')"></span>
            </template>
          </div>
        </div>
      </template>

    </div>
  `;
}

/**
 * Componente Alpine.js da página de Relatório de Abordagens.
 *
 * Gerencia estado do calendário (mês, dia selecionado, dots), carregamento
 * das abordagens do dia via API e filtro local por nome/placa/endereço.
 * Calendário com layout idêntico ao da página Analítico.
 */
function ocorrenciasPage() {
  const agora = new Date();
  return {
    abordagens: [],
    filtro: '',
    loading: false,
    erro: null,
    _searchTimeout: null,

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

    // Mapa de localização (pontos derivados de this.abordagens)
    mapaAnaliticoInst: null,
    _mapaAnaliticoObserver: null,
    modoMapaAnalitico: 'marcadores',
    clusterAnalitico: null,
    heatAnalitico: null,

    get total() {
      return this.abordagens.length;
    },

    get totalPessoas() {
      const ids = new Set();
      for (const ab of this.abordagens) {
        for (const p of (ab.pessoas || [])) ids.add(p.id);
      }
      return ids.size;
    },

    get labelContagem() {
      if (this.filtro && this.filtro.trim()) return 'Resultados da busca';
      if (this.diaSelecionado) {
        return `${String(this.diaSelecionado).padStart(2,'0')}/${String(this._mesSelec).padStart(2,'0')}/${this._anoSelec}`;
      }
      return '—';
    },

    get pontosMapa() {
      return this.abordagens
        .filter(a => a.latitude != null && a.longitude != null)
        .map(a => ({
          lat: a.latitude,
          lng: a.longitude,
          id: a.id,
          dataHora: a.data_hora
            ? new Date(a.data_hora).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
            : '—',
          endereco: a.endereco_texto || '',
          nomes: (a.pessoas || []).map(p => p.nome),
        }));
    },

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

    get abordagensFiltradas() {
      return this.abordagens;
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

    async init() {
      const dataHoje = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(this.diaHoje).padStart(2,'0')}`;
      await Promise.all([
        this.carregarDiasComAbordagem(),
        this.carregarAbordagensDoDia(dataHoje),
      ]);
    },

    async mesMenos() {
      if (this.mesCalendarioAtual === 1) {
        this.mesCalendarioAtual = 12;
        this.anoCalendarioAtual--;
      } else {
        this.mesCalendarioAtual--;
      }
      this.diaSelecionado = null;
      this.abordagens = [];
      this.destroyMapaAnalitico();
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
      this.abordagens = [];
      this.destroyMapaAnalitico();
      await this.carregarDiasComAbordagem();
    },

    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      await this.carregarAbordagensDoDia(dataStr);
    },

    async carregarDiasComAbordagem() {
      const mes = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;
      this.diasComAbordagem = await api.get(`/analytics/dias-com-abordagem?mes=${mes}`).catch(() => []);
    },

    onFiltroInput() {
      clearTimeout(this._searchTimeout);
      const q = this.filtro.trim();
      if (q.length >= 1) {
        this._searchTimeout = setTimeout(() => this.buscarPorTexto(q), 400);
      } else {
        if (this.diaSelecionado) {
          const dataStr = `${this._anoSelec}-${String(this._mesSelec).padStart(2,'0')}-${String(this.diaSelecionado).padStart(2,'0')}`;
          this.carregarAbordagensDoDia(dataStr);
        } else {
          this.abordagens = [];
          this._refreshMapa();
        }
      }
    },

    async buscarPorTexto(q) {
      this.loading = true;
      this.erro = null;
      try {
        const params = new URLSearchParams({ q });
        this.abordagens = await api.get(`/abordagens/?${params}`);
      } catch (e) {
        this.erro = 'Erro ao buscar abordagens. Tente novamente.';
      } finally {
        this.loading = false;
      }
      await this._refreshMapa();
    },

    async carregarAbordagensDoDia(dataStr) {
      this.loading = true;
      this.erro = null;
      try {
        this.abordagens = await api.get(`/abordagens/?data=${dataStr}`);
      } catch (e) {
        this.erro = 'Erro ao carregar abordagens. Tente novamente.';
      } finally {
        this.loading = false;
      }
      await this._refreshMapa();
    },

    async _refreshMapa() {
      this.destroyMapaAnalitico();
      if (this.pontosMapa.length > 0) {
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
      const div = document.getElementById('mapa-relatorio-dia');
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
      const div = document.getElementById('mapa-relatorio-dia');
      if (!div || this.mapaAnaliticoInst) return;
      if (typeof L === 'undefined') return;

      this.mapaAnaliticoInst = L.map(div, { zoomControl: true });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(this.mapaAnaliticoInst);

      const pontos = this.pontosMapa;

      this.clusterAnalitico = L.markerClusterGroup();
      pontos.forEach(p => {
        const marker = L.marker([p.lat, p.lng]);
        const popupEl = document.createElement('div');
        popupEl.style.cssText = 'font-family:monospace;font-size:12px;line-height:1.4;';

        const linhaId = document.createElement('div');
        linhaId.style.fontWeight = '700';
        linhaId.textContent = `#${p.id} · ${p.dataHora}`;
        popupEl.appendChild(linhaId);

        const linhaEndereco = document.createElement('div');
        linhaEndereco.textContent = p.endereco || 'Endereço não informado';
        popupEl.appendChild(linhaEndereco);

        p.nomes.forEach((nome, i) => {
          const linhaNome = document.createElement('div');
          if (i === 0) linhaNome.style.marginTop = '4px';
          linhaNome.textContent = nome;
          popupEl.appendChild(linhaNome);
        });

        const btnAbrir = document.createElement('button');
        btnAbrir.textContent = 'Abrir abordagem';
        btnAbrir.style.cssText = 'margin-top:8px;font-size:0.75rem;padding:0.3rem 0.6rem;border-radius:4px;border:none;cursor:pointer;background:#14B8A6;color:var(--color-bg);font-family:var(--font-data);font-weight:600;';
        btnAbrir.addEventListener('click', () => this.abrirDetalhe(p.id));
        popupEl.appendChild(btnAbrir);

        marker.bindPopup(popupEl);
        this.clusterAnalitico.addLayer(marker);
      });

      const heatPontos = pontos.map(p => [p.lat, p.lng, 1]);
      this.heatAnalitico = L.heatLayer(heatPontos, { radius: 30, blur: 20, maxZoom: 17 });

      this.mapaAnaliticoInst.addLayer(this.clusterAnalitico);

      if (pontos.length === 1) {
        this.mapaAnaliticoInst.setView([pontos[0].lat, pontos[0].lng], 15);
      } else if (pontos.length > 1) {
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
        this.mapaAnaliticoInst.closePopup();
        this.mapaAnaliticoInst.remove();
        this.mapaAnaliticoInst = null;
        this.clusterAnalitico = null;
        this.heatAnalitico = null;
      }
      this.modoMapaAnalitico = 'marcadores';
    },

    abrirDetalhe(id) {
      const appEl = document.querySelector('[x-data]');
      if (appEl && appEl._x_dataStack) {
        appEl._x_dataStack[0]._abordagemId = id;
        appEl._x_dataStack[0].navigate('abordagem-detalhe');
      }
    },

    iniciais(nome) {
      return nome.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },

    nomesPessoas(pessoas) {
      if (!pessoas || !pessoas.length) return '';
      const nomes = pessoas.slice(0, 2).map(p => p.nome.split(' ')[0].toUpperCase());
      const extra = pessoas.length > 2 ? ` +${pessoas.length - 2}` : '';
      return nomes.join(' · ') + extra;
    },

    midias(fotos) {
      return (fotos || []).filter(f => f.tipo === 'midia_abordagem').length;
    },

    formatarDataHora(dt) {
      const d = new Date(dt);
      return d.toLocaleDateString('pt-BR') + ' · ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    },
  };
}
