/**
 * Página de detalhe de abordagem — Argus AI.
 *
 * Exibe dados completos de uma abordagem: pessoas abordadas (clicáveis),
 * veículos, mapa Leaflet, observação, upload de RAP PDF e upload de mídias.
 */

function renderAbordagemDetalhe() {
  return `
    <div x-data="abordagemDetalhePage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Loading inicial -->
      <div x-show="loading" style="text-align:center;padding:48px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="color:var(--color-danger);font-family:var(--font-data);font-size:13px;" x-text="erro"></p>
      </div>

      <!-- Conteúdo principal -->
      <template x-if="!loading && !erro && ab">

        <div style="display:flex;flex-direction:column;gap:12px;">

          <!-- ID + Data/Hora + badge RAP -->
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span style="font-family:var(--font-display);font-size:10px;color:var(--color-text-dim);" x-text="'#' + ab.id"></span>
            <span style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);" x-text="formatarDataHora(ab.data_hora)"></span>
            <template x-if="ab.ocorrencias && ab.ocorrencias.length > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);text-transform:uppercase;letter-spacing:0.08em;">RAP</span>
            </template>
          </div>

          <!-- ABORDADOS -->
          <div class="glass-card card-led-blue" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Abordados</span>
              <div x-show="!ab.pessoas || ab.pessoas.length === 0" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">Nenhum abordado registrado.</div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;">
                <template x-for="p in (ab.pessoas || [])" :key="p.id">
                  <div style="display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;" @click="abrirFicha(p.id)">
                    <div style="width:54px;height:54px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;overflow:hidden;transition:border-color 0.15s;"
                         onmouseover="this.style.borderColor='var(--color-primary)'" onmouseout="this.style.borderColor='rgba(0,212,255,0.2)'">
                      <template x-if="p.foto_principal_url">
                        <img :src="p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                      </template>
                      <template x-if="!p.foto_principal_url">
                        <span style="font-family:var(--font-display);font-size:16px;font-weight:700;color:var(--color-primary);" x-text="iniciais(p.nome)"></span>
                      </template>
                    </div>
                    <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-muted);text-align:center;max-width:56px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                          x-text="p.nome.split(' ')[0]"></span>
                  </div>
                </template>
              </div>
              <p x-show="ab.pessoas && ab.pessoas.length > 0" style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;">Toque para abrir a ficha</p>
            </div>
          </div>

          <!-- VEÍCULOS -->
          <template x-if="ab.veiculos && ab.veiculos.length > 0">
            <div class="glass-card" style="padding:12px;">
              <div style="display:flex;flex-direction:column;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Veículos</span>
                <template x-for="v in ab.veiculos" :key="v.id">
                  <div style="display:flex;align-items:center;gap:10px;padding:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;">
                    <div style="width:52px;height:36px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:3px;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">
                      <template x-if="fotoVeiculo(v.id)">
                        <img :src="fotoVeiculo(v.id)" style="width:100%;height:100%;object-fit:cover;">
                      </template>
                      <template x-if="!fotoVeiculo(v.id)">
                        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><rect x="2" y="7" width="20" height="13" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>
                      </template>
                    </div>
                    <div>
                      <div style="font-family:var(--font-display);font-size:12px;font-weight:700;color:var(--color-primary);letter-spacing:0.1em;" x-text="v.placa"></div>
                      <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);"
                           x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </template>

          <!-- LOCALIZAÇÃO -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Localização</span>
              <template x-if="ab.latitude && ab.longitude">
                <div :id="'mapa-ab-' + ab.id" style="width:100%;height:280px;border-radius:4px;border:1px solid var(--color-border);"></div>
              </template>
              <template x-if="!ab.latitude || !ab.longitude">
                <div style="height:60px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;display:flex;align-items:center;justify-content:center;">
                  <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Coordenadas não disponíveis</span>
                </div>
              </template>
              <template x-if="ab.endereco_texto">
                <div style="display:flex;align-items:center;gap:6px;">
                  <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);flex-shrink:0;"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                  <span style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);" x-text="ab.endereco_texto"></span>
                </div>
              </template>
            </div>
          </div>

          <!-- OBSERVAÇÃO -->
          <template x-if="ab.observacao">
            <div class="glass-card" style="padding:12px;">
              <div style="display:flex;flex-direction:column;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Observação</span>
                <div style="background:var(--color-surface);border:1px solid var(--color-border);border-left:2px solid rgba(0,212,255,0.3);border-radius:4px;padding:10px 12px;font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);line-height:1.5;"
                     x-text="ab.observacao"></div>
              </div>
            </div>
          </template>

          <hr style="border:none;border-top:1px solid var(--color-border);margin:4px 0;">

          <!-- RAP -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Boletim de Ocorrência (RAP)</span>
                <template x-if="ab.ocorrencias && ab.ocorrencias.length > 0">
                  <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);text-transform:uppercase;">Vinculada</span>
                </template>
              </div>

              <!-- RAP(s) já vinculadas -->
              <template x-if="ab.ocorrencias && ab.ocorrencias.length > 0">
                <div style="display:flex;flex-direction:column;gap:6px;">
                  <template x-for="oc in ab.ocorrencias" :key="oc.id">
                    <div style="display:flex;align-items:center;gap:10px;border:1px solid rgba(0,255,136,0.3);background:rgba(0,255,136,0.04);border-radius:4px;padding:10px;">
                      <div style="width:32px;height:32px;border-radius:4px;background:rgba(0,255,136,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-success);"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                      </div>
                      <div style="flex:1;min-width:0;">
                        <div style="font-family:var(--font-display);font-size:11px;color:var(--color-success);" x-text="oc.numero_ocorrencia"></div>
                        <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);"
                             x-text="'Data: ' + new Date(oc.data_ocorrencia).toLocaleDateString('pt-BR')"></div>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <a :href="oc.arquivo_pdf_url" target="_blank"
                           style="color:var(--color-text-dim);display:flex;align-items:center;"
                           title="Abrir PDF">
                          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        </a>
                        <a :href="oc.arquivo_pdf_url"
                           download
                           @click.stop
                           style="display:inline-flex;align-items:center;gap:3px;font-family:var(--font-display);font-size:9px;color:var(--color-primary);text-decoration:none;"
                           title="Baixar PDF">
                          <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                          PDF
                        </a>
                      </div>
                    </div>
                  </template>
                </div>
              </template>

              <!-- Formulário upload RAP (sem RAP) -->
              <template x-if="!ab.ocorrencias || ab.ocorrencias.length === 0">
                <div style="display:flex;flex-direction:column;gap:8px;">
                  <div style="border:1px dashed rgba(0,212,255,0.25);border-radius:4px;padding:12px;display:flex;align-items:center;gap:10px;cursor:pointer;"
                       :style="rapFile ? 'border-color:rgba(0,255,136,0.3);background:rgba(0,255,136,0.04);' : 'background:rgba(0,212,255,0.03);'"
                       @click="$refs.rapInput.click()">
                    <div style="width:32px;height:32px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <div>
                      <div style="font-family:var(--font-display);font-size:11px;color:var(--color-primary);"
                           x-text="rapFile ? rapFile.name : 'Selecionar PDF da RAP'"></div>
                      <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);"
                           x-text="rapFile ? formatarTamanho(rapFile.size) : 'Toque para selecionar o arquivo'"></div>
                    </div>
                    <input type="file" accept="application/pdf" x-ref="rapInput" style="display:none;" @change="rapFile = $event.target.files[0]">
                  </div>
                  <div>
                    <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Número da RAP</div>
                    <input type="text" x-model="rapNumero" placeholder="Ex: RAP 2026/004820"
                      style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 10px;color:var(--color-text);font-family:var(--font-data);font-size:13px;outline:none;">
                  </div>
                  <div>
                    <div style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Data da Ocorrência</div>
                    <input type="text" x-model="rapData" placeholder="DD/MM/AAAA" maxlength="10"
                      @input="rapData = formatarData($event.target.value)"
                      style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 10px;color:var(--color-text);font-family:var(--font-data);font-size:13px;outline:none;">
                  </div>
                  <p x-show="rapErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="rapErro"></p>
                  <button @click="enviarRap()"
                          :disabled="!rapFile || !rapNumero || !rapData || enviandoRap"
                          style="width:100%;padding:10px;background:var(--color-primary);color:var(--color-bg);font-family:var(--font-display);font-size:12px;font-weight:700;border:none;border-radius:4px;cursor:pointer;letter-spacing:0.08em;"
                          :style="(!rapFile || !rapNumero || !rapData || enviandoRap) ? 'opacity:0.4;cursor:not-allowed;' : 'opacity:1;'">
                    <span x-show="!enviandoRap">ENVIAR OCORRÊNCIA</span>
                    <span x-show="enviandoRap">ENVIANDO...</span>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- MÍDIAS -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Mídias</span>
                <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);">fotos · vídeos · autorizações</span>
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <template x-for="f in midiasAbordagem" :key="f.id">
                  <div style="width:64px;height:64px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:4px;overflow:hidden;cursor:pointer;position:relative;"
                       @click="fotoAmpliada = f.arquivo_url">
                    <template x-if="/\\.(mp4|mov|avi|webm)/i.test(f.arquivo_url)">
                      <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;">
                        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/></svg>
                        <span style="font-family:var(--font-display);font-size:7px;color:var(--color-primary);">VID</span>
                      </div>
                    </template>
                    <template x-if="!/\\.(mp4|mov|avi|webm)/i.test(f.arquivo_url)">
                      <img :src="f.arquivo_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                    </template>
                    <!-- Botão download -->
                    <button @click.stop="downloadMidia(f)"
                       style="position:absolute;bottom:2px;right:2px;background:rgba(0,0,0,0.65);border-radius:3px;padding:2px;display:flex;align-items:center;justify-content:center;cursor:pointer;border:none;"
                       title="Baixar">
                      <svg width="12" height="12" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                    </button>
                  </div>
                </template>
                <!-- Botão adicionar -->
                <div style="width:64px;height:64px;border:1px dashed rgba(0,212,255,0.25);border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;cursor:pointer;background:rgba(0,212,255,0.03);"
                     :style="enviandoMidia ? 'opacity:0.5;cursor:not-allowed;' : ''"
                     @click="!enviandoMidia && $refs.midiaInput.click()">
                  <template x-if="!enviandoMidia">
                    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-primary);"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </template>
                  <template x-if="enviandoMidia">
                    <div style="width:16px;height:16px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;"></div>
                  </template>
                  <span style="font-family:var(--font-display);font-size:8px;color:var(--color-text-dim);" x-show="!enviandoMidia">ADD</span>
                  <input type="file" accept="image/*,video/*,application/pdf" x-ref="midiaInput" style="display:none;"
                         @change="enviarMidia($event.target.files[0])">
                </div>
              </div>
              <p x-show="midiaErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="midiaErro"></p>
            </div>
          </div>

        </div>
      </template>

      <!-- Modal foto ampliada -->
      <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
           style="position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
        <img :src="fotoAmpliada" style="max-width:100%;max-height:80vh;border-radius:4px;" @click.stop>
      </div>

    </div>
  `;
}

function abordagemDetalhePage() {
  return {
    ab: null,
    loading: true,
    erro: null,
    fotoAmpliada: null,
    rapFile: null,
    rapNumero: '',
    rapData: '',
    rapErro: null,
    enviandoRap: false,
    enviandoMidia: false,
    midiaErro: null,
    _mapa: null,
    _mapaObserver: null,

    get midiasAbordagem() {
      return (this.ab && this.ab.fotos ? this.ab.fotos : []).filter(f => f.tipo === 'midia_abordagem');
    },

    async init() {
      const appEl = document.querySelector('[x-data]');
      const abordagemId = appEl && appEl._x_dataStack && appEl._x_dataStack[0] && appEl._x_dataStack[0]._abordagemId;
      if (!abordagemId) {
        this.erro = 'ID da abordagem não encontrado.';
        this.loading = false;
        return;
      }
      try {
        this.ab = await api.get(`/abordagens/${abordagemId}`);
      } catch (e) {
        this.erro = 'Erro ao carregar abordagem.';
      } finally {
        this.loading = false;
      }
      if (this.ab && this.ab.latitude && this.ab.longitude) {
        this.$nextTick(() => this._initMapa());
      }
    },

    _initMapa() {
      if (this._mapaObserver) this._mapaObserver.disconnect();
      const divId = 'mapa-ab-' + this.ab.id;
      const tryInit = () => {
        const div = document.getElementById(divId);
        if (!div) return false;
        if (this._mapa) { this._mapa.remove(); this._mapa = null; }
        this._mapa = L.map(div, { zoomControl: true, dragging: true, scrollWheelZoom: true })
          .setView([this.ab.latitude, this.ab.longitude], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap'
        }).addTo(this._mapa);
        L.circleMarker([this.ab.latitude, this.ab.longitude], {
          radius: 8, color: '#00D4FF', fillColor: '#00D4FF', fillOpacity: 0.8, weight: 2
        }).addTo(this._mapa);
        return true;
      };
      if (!tryInit()) {
        this._mapaObserver = new MutationObserver(() => {
          if (tryInit()) this._mapaObserver.disconnect();
        });
        this._mapaObserver.observe(document.body, { childList: true, subtree: true });
      }
    },

    fotoVeiculo(veiculoId) {
      const f = (this.ab && this.ab.fotos ? this.ab.fotos : []).find(
        f => f.veiculo_id === veiculoId && f.tipo === 'veiculo'
      );
      return f ? f.arquivo_url : null;
    },

    abrirFicha(pessoaId) {
      const appEl = document.querySelector('[x-data]');
      if (appEl && appEl._x_dataStack) {
        appEl._x_dataStack[0]._pessoaId = pessoaId;
        appEl._x_dataStack[0].navigate('pessoa-detalhe');
      }
    },

    async enviarRap() {
      this.rapErro = null;
      const partes = this.rapData.split('/');
      if (partes.length !== 3) { this.rapErro = 'Data inválida. Use DD/MM/AAAA.'; return; }
      const [dia, mes, ano] = partes.map(Number);
      if (!dia || !mes || !ano || dia < 1 || dia > 31 || mes < 1 || mes > 12 || ano < 2000 || ano > 2100) {
        this.rapErro = 'Data inválida. Verifique dia, mês e ano.';
        return;
      }
      const dataIso = partes[2] + '-' + partes[1].padStart(2, '0') + '-' + partes[0].padStart(2, '0');
      this.enviandoRap = true;
      try {
        const result = await api.uploadFile('/ocorrencias/', this.rapFile, {
          numero_ocorrencia: this.rapNumero,
          abordagem_id: this.ab.id,
          data_ocorrencia: dataIso,
        }, 'arquivo_pdf');
        this.ab = { ...this.ab, ocorrencias: [...(this.ab.ocorrencias || []), result] };
        this.rapFile = null;
        this.rapNumero = '';
        this.rapData = '';
      } catch (e) {
        this.rapErro = e?.message || 'Erro ao enviar RAP. Verifique o arquivo e tente novamente.';
      } finally {
        this.enviandoRap = false;
      }
    },

    async downloadMidia(foto) {
      try {
        const response = await api.downloadBlob(`/fotos/${foto.id}/download`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const disposition = response.headers.get('Content-Disposition');
        const match = disposition && disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)["']?/i);
        a.download = match ? decodeURIComponent(match[1].trim()) : `midia_${foto.id}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (e) {
        this.midiaErro = 'Erro ao baixar mídia. Tente novamente.';
      }
    },

    async enviarMidia(file) {
      if (!file) return;
      this.midiaErro = null;
      this.enviandoMidia = true;
      try {
        const result = await api.uploadFile('/fotos/midias', file, {
          abordagem_id: this.ab.id,
        });
        this.ab = { ...this.ab, fotos: [...(this.ab.fotos || []), result] };
      } catch (e) {
        this.midiaErro = 'Erro ao enviar mídia. Tente novamente.';
      } finally {
        this.enviandoMidia = false;
      }
    },

    iniciais(nome) {
      return nome.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },

    formatarDataHora(dt) {
      const d = new Date(dt);
      return d.toLocaleDateString('pt-BR') + ' · ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    },

    formatarTamanho(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    formatarData(v) {
      const nums = v.replace(/\D/g, '');
      if (nums.length <= 2) return nums;
      if (nums.length <= 4) return nums.slice(0, 2) + '/' + nums.slice(2);
      return nums.slice(0, 2) + '/' + nums.slice(2, 4) + '/' + nums.slice(4, 8);
    },
  };
}
