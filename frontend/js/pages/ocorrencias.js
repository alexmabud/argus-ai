/**
 * Página de listagem de abordagens (Relatório de Abordagens) — Argus AI.
 *
 * Lista as abordagens realizadas pelo usuário logado, com filtro local
 * por nome ou placa, badge de RAP vinculada e navegação para detalhe.
 */

function renderOcorrencias() {
  return `
    <div x-data="ocorrenciasPage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.1em;margin:0;">
          RELATÓRIO DE ABORDAGENS
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;margin-top:4px;"
           x-text="loading ? 'CARREGANDO...' : total + ' ABORDAGENS'">
        </p>
      </div>

      <!-- Busca local -->
      <div style="display:flex;align-items:center;gap:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 12px;">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="search" x-model="filtro" placeholder="Buscar por nome, placa, endereço..."
          style="background:none;border:none;outline:none;color:var(--color-text);font-family:var(--font-data);font-size:13px;width:100%;">
      </div>

      <!-- Loading -->
      <div x-show="loading" style="text-align:center;padding:32px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-danger);" x-text="erro"></p>
        <button @click="carregar()" class="btn btn-secondary" style="margin-top:8px;width:auto;padding:6px 16px;">Tentar novamente</button>
      </div>

      <!-- Lista -->
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
                    <img :src="p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
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
              <div style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
                   x-text="formatarDataHora(ab.data_hora)"></div>
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

      <!-- Vazio -->
      <div x-show="!loading && !erro && abordagensFiltradas.length === 0" style="text-align:center;padding:32px 0;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-text-muted);">
          <span x-show="filtro">Nenhum resultado para "<span x-text="filtro"></span>"</span>
          <span x-show="!filtro">Nenhuma abordagem registrada ainda.</span>
        </p>
      </div>

      <!-- Carregar mais -->
      <div x-show="!loading && temMais" style="text-align:center;">
        <button @click="carregarMais()" :disabled="carregandoMais" class="btn btn-secondary"
                style="width:auto;padding:8px 24px;font-size:12px;">
          <span x-show="!carregandoMais">Carregar mais</span>
          <span x-show="carregandoMais">Carregando...</span>
        </button>
      </div>

    </div>
  `;
}

function ocorrenciasPage() {
  return {
    abordagens: [],
    filtro: '',
    loading: true,
    carregandoMais: false,
    erro: null,
    skip: 0,
    limit: 20,
    total: 0,
    temMais: false,

    get abordagensFiltradas() {
      if (!this.filtro.trim()) return this.abordagens;
      const q = this.filtro.toLowerCase();
      return this.abordagens.filter(ab => {
        const nomes = (ab.pessoas || []).map(p => p.nome.toLowerCase()).join(' ');
        const placas = (ab.veiculos || []).map(v => v.placa.toLowerCase()).join(' ');
        const end = (ab.endereco_texto || '').toLowerCase();
        return nomes.includes(q) || placas.includes(q) || end.includes(q);
      });
    },

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.loading = true;
      this.erro = null;
      this.skip = 0;
      try {
        const data = await api.get(`/abordagens/?skip=0&limit=${this.limit}`);
        this.abordagens = data;
        this.total = data.length;
        this.temMais = data.length === this.limit;
      } catch (e) {
        this.erro = 'Erro ao carregar abordagens. Tente novamente.';
      } finally {
        this.loading = false;
      }
    },

    async carregarMais() {
      this.carregandoMais = true;
      this.skip += this.limit;
      try {
        const data = await api.get(`/abordagens/?skip=${this.skip}&limit=${this.limit}`);
        this.abordagens = [...this.abordagens, ...data];
        this.total = this.abordagens.length;
        this.temMais = data.length === this.limit;
      } catch (e) {
        this.skip -= this.limit;
      } finally {
        this.carregandoMais = false;
      }
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
