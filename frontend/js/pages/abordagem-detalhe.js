/**
 * Página de detalhe de abordagem — Argus AI.
 *
 * Exibe dados completos de uma abordagem: pessoas abordadas (clicáveis),
 * veículos, mapa Leaflet, observação editável (com ditado por voz), upload
 * de RAP PDF e upload de mídias.
 */

function renderAbordagemDetalhe() {
  return `
    <div x-data="{ ...abordagemDetalhePage(), ...personPhotoModal(), ...cadastroPessoaModal(), ...confirmDialog() }" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

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
          <!-- position:relative + z-index: .glass-card cria stacking context próprio
               (backdrop-filter) — sem isso, o dropdown do autocomplete (position:absolute
               interno) fica preso nesse contexto e o card VEÍCULOS (irmão seguinte, sem
               z-index) pinta por cima dele quando o dropdown ultrapassa a borda do card. -->
          <div class="glass-card card-led-blue" style="padding:12px;position:relative;z-index:2;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Abordados</span>
              <div x-show="!ab.pessoas || ab.pessoas.length === 0" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">Nenhum abordado registrado.</div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;">
                <template x-for="p in (ab.pessoas || [])" :key="p.id">
                  <div style="display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;position:relative;"
                       @click="openPhotoModal(p.foto_principal_url || null, p.id, p, null, podeEditar() ? { tituloBotao: 'Remover abordado', mensagem: 'Remover este abordado da abordagem? Esta ação não pode ser desfeita.', onConfirm: () => removerPessoa(p.id) } : null)">
                    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
                      <div style="width:54px;height:54px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;overflow:hidden;transition:border-color 0.15s;"
                           class="hov-border-primary">
                        <template x-if="p.foto_principal_url">
                          <img :src="p.foto_principal_thumb_url || p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                        </template>
                        <template x-if="!p.foto_principal_url">
                          <span style="font-family:var(--font-display);font-size:16px;font-weight:700;color:var(--color-primary);" x-text="iniciais(p.nome)"></span>
                        </template>
                      </div>
                      <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-muted);text-align:center;max-width:56px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                            x-text="p.nome.split(' ')[0]"></span>
                    </div>
                  </div>
                </template>
              </div>
              <p x-show="ab.pessoas && ab.pessoas.length > 0" style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;">Toque para abrir a ficha</p>

              <template x-if="podeEditar()">
                <div>
                  <button x-show="!adicionandoAbordado" @click="adicionandoAbordado = true"
                          style="font-family:var(--font-display);font-size:11px;color:var(--color-primary);background:transparent;border:1px dashed rgba(0,212,255,0.3);border-radius:4px;padding:6px 10px;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                    + Adicionar abordado
                  </button>

                  <div x-show="adicionandoAbordado" x-cloak style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
                    <div x-data="autocompleteComponent('pessoa')" data-autocomplete="pessoa" style="position:relative;">
                      <input type="text" :value="query"
                             @input="query = $event.target.value; onInput()"
                             @focus="showDropdown = results.length > 0 || noResults"
                             placeholder="Buscar por nome ou CPF..." style="width:100%;">

                      <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
                           style="position:absolute;z-index:20;width:100%;margin-top:4px;max-height:14rem;overflow-y:auto;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">
                        <template x-for="item in results" :key="item.id">
                          <button @click="select(item); $dispatch('abordado-selecionado', { pessoa: item })"
                                  style="width:100%;text-align:left;padding:8px 12px;font-family:var(--font-body);font-size:14px;color:var(--color-text);border:none;background:transparent;cursor:pointer;border-bottom:1px solid var(--color-border);display:flex;flex-direction:column;gap:2px;"
                                  class="hov-row-surface">
                            <span x-text="getLabel(item)"></span>
                            <span x-show="getSubLabel(item)" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="getSubLabel(item)"></span>
                          </button>
                        </template>
                        <div x-show="noResults" style="padding:12px;font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);">
                          <p>Nenhuma pessoa encontrada.</p>
                          <button @click="$dispatch('cadastrar-abordado-solicitado', { query: query })"
                                  style="margin-top:8px;width:100%;text-align:left;color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                            + Cadastrar novo abordado
                          </button>
                        </div>
                      </div>

                      <p x-show="cpfErro" x-text="cpfErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);margin-top:4px;"></p>
                    </div>
                    <button @click="adicionandoAbordado = false; erroVincularPessoa = null"
                            style="align-self:flex-start;font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);background:transparent;border:none;cursor:pointer;">
                      Cancelar
                    </button>
                    <p x-show="erroVincularPessoa" x-text="erroVincularPessoa" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);"></p>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- VEÍCULOS -->
          <!-- position:relative + z-index: mesmo motivo do card ABORDADOS acima —
               o dropdown do autocomplete de veículo não pode ficar preso atrás do
               card LOCALIZAÇÃO (irmão seguinte). -->
          <template x-if="(ab.veiculos && ab.veiculos.length > 0) || podeEditar()">
            <div class="glass-card" style="padding:12px;position:relative;z-index:1;">
              <div style="display:flex;flex-direction:column;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Veículos</span>
                <div x-show="!ab.veiculos || ab.veiculos.length === 0" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">Nenhum veículo registrado.</div>
                <template x-for="v in ab.veiculos" :key="v.id">
                  <div style="display:flex;align-items:center;gap:10px;padding:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;position:relative;cursor:pointer;"
                       @click="openPhotoModal(fotoVeiculo(v.id), v.pessoa_id || null, null, v, podeEditar() ? { tituloBotao: 'Remover veículo', mensagem: 'Remover este veículo da abordagem? Esta ação não pode ser desfeita.', onConfirm: () => removerVeiculo(v.id) } : null)">
                    <div style="width:52px;height:36px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:3px;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">
                      <template x-if="fotoVeiculo(v.id)">
                        <img :src="fotoVeiculo(v.id)" style="width:100%;height:100%;object-fit:cover;">
                      </template>
                      <template x-if="!fotoVeiculo(v.id)">
                        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><rect x="2" y="7" width="20" height="13" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>
                      </template>
                    </div>
                    <div>
                      <span style="font-family:var(--font-data);font-size:12px;font-weight:700;color:var(--color-text);letter-spacing:0.1em;background:var(--color-surface-hover);padding:0.125rem 0.375rem;border-radius:2px;border:1px solid var(--color-border);" x-text="formatarPlaca(v.placa)"></span>
                      <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);margin-top:3px;"
                           x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></div>
                    </div>
                  </div>
                </template>

                <template x-if="podeEditar()">
                  <div>
                    <button x-show="!adicionandoVeiculo" @click="adicionandoVeiculo = true"
                            style="font-family:var(--font-display);font-size:11px;color:var(--color-primary);background:transparent;border:1px dashed rgba(0,212,255,0.3);border-radius:4px;padding:6px 10px;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                      + Adicionar veículo
                    </button>

                    <div x-show="adicionandoVeiculo" x-cloak style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
                      <div x-data="autocompleteComponent('veiculo')" data-autocomplete="veiculo" style="position:relative;">
                        <input type="text" :value="query"
                               @input="query = formatarPlaca($event.target.value); onInput()"
                               @focus="showDropdown = results.length > 0 || noResults"
                               placeholder="Buscar por placa..." maxlength="8" style="width:100%;">

                        <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
                             style="position:absolute;z-index:20;width:100%;margin-top:4px;max-height:14rem;overflow-y:auto;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">
                          <template x-for="item in results" :key="item.id">
                            <button @click="select(item); $dispatch('veiculo-selecionado', { veiculo: item })"
                                    style="width:100%;text-align:left;padding:8px 12px;font-family:var(--font-body);font-size:14px;color:var(--color-text);border:none;background:transparent;cursor:pointer;border-bottom:1px solid var(--color-border);"
                                    class="hov-row-surface"
                                    x-text="getLabel(item)">
                            </button>
                          </template>
                          <div x-show="noResults" style="padding:12px;font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);">
                            <p>Nenhum veículo encontrado.</p>
                            <button @click="showDropdown = false; mostrandoNovoVeiculo = true; novoVeiculo.placa = query"
                                    style="margin-top:8px;width:100%;text-align:left;color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                              + Cadastrar novo veículo
                            </button>
                          </div>
                        </div>
                      </div>

                      <div x-show="mostrandoNovoVeiculo" x-cloak style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:8px;">
                        <div>
                          <label class="login-field-label">Placa *</label>
                          <input type="text" :value="novoVeiculo.placa"
                                 @input="novoVeiculo.placa = formatarPlaca($event.target.value)"
                                 placeholder="ABC-1234" maxlength="8" style="text-transform:uppercase;">
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                          <div>
                            <label class="login-field-label">Modelo</label>
                            <input type="text" class="input-upper" x-model="novoVeiculo.modelo" placeholder="Ex: Gol">
                          </div>
                          <div>
                            <label class="login-field-label">Cor</label>
                            <select x-model="corVeiculoDropdown" @change="onCorVeiculoChange()"
                                    style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px;font-size:13px;color:var(--color-text);font-family:var(--font-body);box-sizing:border-box;">
                              <option value="">Selecione...</option>
                              <template x-for="c in (window.CORES_VEICULO || [])" :key="c"><option :value="c" x-text="c"></option></template>
                              <option value="__outra__">Outra...</option>
                            </select>
                            <input x-show="corVeiculoDropdown === '__outra__'" type="text" class="input-upper" x-model="novoVeiculo.cor" placeholder="Digite a cor" style="margin-top:6px;">
                          </div>
                          <div>
                            <label class="login-field-label">Ano</label>
                            <input type="number" x-model="novoVeiculo.ano" placeholder="2020" min="1900" max="2100">
                          </div>
                        </div>
                        <button @click="criarEVincularVeiculo()" class="btn btn-primary" :disabled="salvandoVeiculo || !novoVeiculo.placa.trim()">
                          <span x-show="!salvandoVeiculo">Salvar e adicionar</span>
                          <span x-show="salvandoVeiculo" style="display:flex;align-items:center;justify-content:center;gap:8px;">
                            <span class="spinner"></span> Salvando...
                          </span>
                        </button>
                      </div>

                      <button @click="adicionandoVeiculo = false; mostrandoNovoVeiculo = false; erroVincularVeiculo = null"
                              style="align-self:flex-start;font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);background:transparent;border:none;cursor:pointer;">
                        Cancelar
                      </button>
                      <p x-show="erroVincularVeiculo" x-text="erroVincularVeiculo" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);"></p>
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
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Observação</span>
                <button x-show="voiceSupported && podeEditar()" @click="toggleVoice()"
                        style="font-family:var(--font-data);font-size:11px;padding:4px 10px;border-radius:4px;cursor:pointer;border:none;transition:all 0.15s;"
                        :style="recording
                          ? 'background:rgba(255,107,0,0.2);color:var(--color-danger);border:1px solid rgba(255,107,0,0.4);box-shadow:0 0 8px rgba(255,107,0,0.3);'
                          : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'">
                  <span x-text="recording ? 'PARAR' : 'VOZ'"></span>
                </button>
              </div>
              <textarea class="input-upper" x-model="observacaoEdit" rows="3" placeholder="Descreva a abordagem..." :disabled="!podeEditar()"></textarea>
              <div x-show="podeEditar()" style="display:flex;align-items:center;gap:8px;">
                <button @click="salvarObservacao()" class="btn btn-primary" style="padding:8px 16px;"
                        :disabled="salvandoObservacao || observacaoEdit.trim() === (ab.observacao || '')">
                  <span x-show="!salvandoObservacao">Salvar observação</span>
                  <span x-show="salvandoObservacao" style="display:flex;align-items:center;gap:8px;">
                    <span class="spinner"></span> Salvando...
                  </span>
                </button>
              </div>
              <p x-show="observacaoErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="observacaoErro"></p>
            </div>
          </div>

          <!-- MÍDIAS -->
          <div class="glass-card" style="padding:12px;">
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Mídias</span>
                <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);">Fotos dessa abordagem</span>
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <template x-for="f in midiasAbordagem()" :key="f.id">
                  <div style="width:64px;height:64px;background:var(--color-surface-hover);border:1px solid var(--color-border);border-radius:4px;overflow:hidden;cursor:pointer;position:relative;"
                       @click="fotoAmpliada = f.arquivo_url">
                    <img :src="f.thumbnail_url || f.arquivo_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                    <button x-show="isAdmin" @click.stop="apagarFoto(f.id)"
                       class="hov-icon-danger"
                       style="position:absolute;top:2px;right:2px;width:18px;height:18px;display:flex;align-items:center;justify-content:center;background:rgba(5,10,15,0.75);color:var(--color-text-muted);border:none;border-radius:2px;cursor:pointer;font-size:10px;line-height:1;padding:0;"
                       title="Apagar mídia">
                      ✕
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
                  <input type="file" accept="image/*,application/pdf" x-ref="midiaInput" style="display:none;"
                         @change="enviarMidia($event.target.files[0])">
                </div>
              </div>
              <p x-show="midiaErro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="midiaErro"></p>
            </div>
          </div>

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

        </div>
      </template>

      ${personPhotoModalHTML()}
      ${cadastroPessoaModalHTML()}
      ${confirmDialogHTML()}

      <!-- Foto ampliada (mídia da abordagem — sem pessoa vinculada) -->
      <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
           style="position:fixed;top:var(--header-height);left:0;right:0;bottom:var(--bottom-nav-height);background:rgba(5,10,15,0.85);z-index:50;display:flex;align-items:center;justify-content:center;padding:1rem;">
        <img :src="fotoAmpliada" @click.stop="fotoAmpliada = null"
             style="max-width:min(90vw,480px);max-height:80vh;border-radius:4px;display:block;cursor:pointer;object-fit:contain;">
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
    isAdmin: !!(auth.getUser()?.is_admin || auth.getUser()?.is_super_admin),
    adicionandoAbordado: false,
    vinculandoPessoa: false,
    erroVincularPessoa: null,
    adicionandoVeiculo: false,
    vinculandoVeiculo: false,
    mostrandoNovoVeiculo: false,
    novoVeiculo: { placa: '', modelo: '', cor: '', ano: '' },
    corVeiculoDropdown: '',
    salvandoVeiculo: false,
    erroVincularVeiculo: null,
    rapFile: null,
    rapNumero: '',
    rapData: '',
    rapErro: null,
    enviandoRap: false,
    enviandoMidia: false,
    midiaErro: null,
    observacaoEdit: '',
    salvandoObservacao: false,
    observacaoErro: null,
    recording: false,
    voiceSupported: typeof webkitSpeechRecognition !== "undefined" || typeof SpeechRecognition !== "undefined",
    _mapa: null,
    _mapaObserver: null,

    // Método (não getter) de propósito: o x-data raiz desta página faz spread
    // de múltiplos objetos (`{ ...abordagemDetalhePage(), ...personPhotoModal() }`),
    // e o Alpine congela getters em valores estáticos nesse cenário (mesmo bug
    // documentado em fotosRosto() de pessoa-detalhe.js). Chamado como função
    // no template (`midiasAbordagem()`) continua reativo.
    midiasAbordagem() {
      return (this.ab && this.ab.fotos ? this.ab.fotos : []).filter(f => f.tipo === 'midia_abordagem');
    },

    // Método (não getter) pelo mesmo motivo de midiasAbordagem() acima.
    podeEditar() {
      const me = auth.getUser();
      return !!(this.ab && me && (this.ab.usuario_id === me.id || this.isAdmin));
    },

    async vincularPessoa(pessoa) {
      if (this.vinculandoPessoa) return;
      this.erroVincularPessoa = null;
      this.vinculandoPessoa = true;
      try {
        const result = await api.post(`/abordagens/${this.ab.id}/pessoas`, { pessoa_id: pessoa.id });
        this.ab = result;
        this.adicionandoAbordado = false;
      } catch (e) {
        this.erroVincularPessoa = e?.message || 'Erro ao vincular pessoa. Tente novamente.';
      } finally {
        this.vinculandoPessoa = false;
      }
    },

    async removerPessoa(pessoaId) {
      try {
        await api.delete(`/abordagens/${this.ab.id}/pessoas/${pessoaId}`);
        this.ab = { ...this.ab, pessoas: this.ab.pessoas.filter(p => p.id !== pessoaId) };
      } catch (e) {
        showToast(e?.message || 'Erro ao remover abordado', 'error');
      }
    },

    // Hook de cadastroPessoaModal() (ver frontend/js/components/cadastro-pessoa-modal.js):
    // chamado no lugar de navegar pra ficha após criar a pessoa — vincula
    // direto na abordagem aberta.
    onPessoaCriada(pessoa) {
      this.vincularPessoa(pessoa);
    },

    async vincularVeiculo(veiculo) {
      if (this.vinculandoVeiculo) return;
      this.erroVincularVeiculo = null;
      this.vinculandoVeiculo = true;
      try {
        const result = await api.post(`/abordagens/${this.ab.id}/veiculos`, { veiculo_id: veiculo.id });
        this.ab = result;
        this.adicionandoVeiculo = false;
        this.mostrandoNovoVeiculo = false;
      } catch (e) {
        this.erroVincularVeiculo = e?.message || 'Erro ao vincular veículo. Tente novamente.';
      } finally {
        this.vinculandoVeiculo = false;
      }
    },

    async removerVeiculo(veiculoId) {
      try {
        await api.delete(`/abordagens/${this.ab.id}/veiculos/${veiculoId}`);
        this.ab = { ...this.ab, veiculos: this.ab.veiculos.filter(v => v.id !== veiculoId) };
      } catch (e) {
        showToast(e?.message || 'Erro ao remover veículo', 'error');
      }
    },

    onCorVeiculoChange() {
      this.novoVeiculo.cor = this.corVeiculoDropdown === '__outra__' ? '' : this.corVeiculoDropdown;
    },

    async criarEVincularVeiculo() {
      if (this.salvandoVeiculo || !this.novoVeiculo.placa.trim()) return;
      this.salvandoVeiculo = true;
      this.erroVincularVeiculo = null;
      try {
        const data = { placa: this.novoVeiculo.placa.trim() };
        if (this.novoVeiculo.modelo.trim()) data.modelo = this.novoVeiculo.modelo.trim();
        if (this.novoVeiculo.cor.trim()) data.cor = this.novoVeiculo.cor.trim();
        if (this.novoVeiculo.ano) data.ano = parseInt(this.novoVeiculo.ano, 10);
        const veiculo = await api.post('/veiculos/', data);
        await this.vincularVeiculo(veiculo);
        // vincularVeiculo() nunca relança erro (fica só em erroVincularVeiculo) —
        // só limpa o formulário se o vínculo realmente deu certo, senão o
        // veículo fica órfão no banco e o usuário perde o que digitou.
        if (!this.erroVincularVeiculo) {
          this.novoVeiculo = { placa: '', modelo: '', cor: '', ano: '' };
          this.corVeiculoDropdown = '';
        }
      } catch (e) {
        this.erroVincularVeiculo = e?.message || 'Erro ao cadastrar veículo. Tente novamente.';
      } finally {
        this.salvandoVeiculo = false;
      }
    },

    async init() {
      this.$el.addEventListener('abordado-selecionado', (e) => this.vincularPessoa(e.detail.pessoa));
      this.$el.addEventListener('cadastrar-abordado-solicitado', (e) => this.abrirCadastroPessoa(e.detail.query));
      this.$el.addEventListener('veiculo-selecionado', (e) => this.vincularVeiculo(e.detail.veiculo));
      const appEl = document.querySelector('[x-data]');
      const abordagemId = appEl && appEl._x_dataStack && appEl._x_dataStack[0] && appEl._x_dataStack[0]._abordagemId;
      if (!abordagemId) {
        this.erro = 'ID da abordagem não encontrado.';
        this.loading = false;
        return;
      }
      try {
        this.ab = await api.get(`/abordagens/${abordagemId}`);
        this.observacaoEdit = this.ab.observacao || '';
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
        criarControleFullscreenMapa().addTo(this._mapa);
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
      return f ? (f.thumbnail_url || f.arquivo_url) : null;
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

    async salvarObservacao() {
      this.observacaoErro = null;
      this.salvandoObservacao = true;
      try {
        const result = await api.patch(`/abordagens/${this.ab.id}`, {
          observacao: this.observacaoEdit.trim() || null,
        });
        this.ab = { ...this.ab, observacao: result.observacao };
        this.observacaoEdit = result.observacao || '';
      } catch (e) {
        this.observacaoErro = e?.message || 'Erro ao salvar observação. Tente novamente.';
      } finally {
        this.salvandoObservacao = false;
      }
    },

    toggleVoice() {
      if (this.recording) {
        stopVoice();
        this.recording = false;
      } else {
        this.observacaoErro = null;
        const _voiceBase = this.observacaoEdit;
        const started = startVoice(
          (text, isFinal) => {
            if (isFinal) {
              this.observacaoEdit = _voiceBase
                ? (_voiceBase + " " + text).trim()
                : text.trim();
            }
          },
          () => { this.recording = false; },
          (errorType) => {
            this.recording = false;
            const msgs = {
              "not-allowed":    "Permissão de microfone negada. Habilite o microfone nas configurações do navegador.",
              "no-speech":      "Nenhuma fala detectada. Tente novamente.",
              "audio-capture":  "Microfone não encontrado. Verifique o hardware.",
              "network":        "Erro de rede no reconhecimento de voz.",
              "service-not-allowed": "Serviço de reconhecimento de voz não permitido neste contexto.",
            };
            this.observacaoErro = msgs[errorType] || `Erro de reconhecimento de voz: ${errorType}`;
          }
        );
        if (started) this.recording = true;
      }
    },

    async apagarFoto(fotoId) {
      if (!confirm("Apagar esta mídia? Esta ação não pode ser desfeita.")) return;
      try {
        await api.delete(`/fotos/${fotoId}`);
        this.ab = { ...this.ab, fotos: this.ab.fotos.filter(f => f.id !== fotoId) };
        showToast("Mídia apagada com sucesso!", "success");
      } catch (err) {
        showToast(err?.message || "Erro ao apagar mídia", "error");
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
