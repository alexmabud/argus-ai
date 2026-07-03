/**
 * Página de consulta unificada — Argus AI.
 *
 * Seções independentes: busca de pessoa (nome/CPF ou foto),
 * filtros por endereço e busca por veículo. Cada seção retorna
 * a ficha do abordado como resultado. Estética cyberpunk tática.
 */
function renderConsulta() {
  return `
    <div x-data="{ ...consultaPage(), ...personPhotoModal() }" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header da página -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.08em;">
          Consulta Operacional
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">
          Busca Integrada // Pessoa / Endereço / Veículo
        </p>
      </div>

      <!-- Pessoa -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoa</span>
        </div>

        <!-- Campo texto -->
        <div style="position:relative;">
          <input type="text" :value="query"
                 @input="onInputPessoa($event.target.value)"
                 placeholder="NOME COMPLETO OU CPF..."
                 inputmode="text"
                 style="padding-left:40px;">
          <svg style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--color-text-dim);width:18px;height:18px;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>
        <p x-show="cpfBuscaErro" x-text="cpfBuscaErro"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);margin-top:4px;"></p>

        <!-- Separador -->
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="flex:1;height:1px;background:var(--color-border);"></div>
          <span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span>
          <div style="flex:1;height:1px;background:var(--color-border);"></div>
        </div>

        <!-- Reconhecimento Facial -->
        <div x-show="!fotoFile" style="display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:4px;border:1px solid rgba(0,212,255,0.15);background:rgba(0,212,255,0.02);">
          <span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;">Reconhecimento Facial</span>
          <div style="display:flex;flex-direction:row;flex-wrap:nowrap;gap:8px;">
            <button @click="$refs.fotoInput.click()"
                    class="hov-cta-card"
                    style="flex:1;display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 12px;border-radius:4px;border:2px dashed rgba(0,212,255,0.3);background:rgba(0,212,255,0.03);cursor:pointer;transition:all 150ms;">
              <div style="width:40px;height:40px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;color:var(--color-primary);">
                <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
                </svg>
              </div>
              <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-primary);text-align:center;">Enviar arquivo</p>
            </button>
            <button @click="$refs.fotoInputCamera.click()"
                    class="hov-cta-card"
                    style="flex:1;display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 12px;border-radius:4px;border:2px dashed rgba(0,212,255,0.3);background:rgba(0,212,255,0.03);cursor:pointer;transition:all 150ms;">
              <div style="width:40px;height:40px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;color:var(--color-primary);">
                <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/>
                </svg>
              </div>
              <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-primary);text-align:center;">Tirar foto agora</p>
            </button>
          </div>
        </div>
        <input type="file" x-ref="fotoInput" accept="image/jpeg,image/png,image/webp"
               class="hidden" @change="onFotoSelect($event)">
        <input type="file" x-ref="fotoInputCamera" accept="image/*" capture="environment"
               class="hidden" @change="onFotoSelect($event)">

        <!-- Preview da foto -->
        <div x-show="fotoFile" style="display:flex;align-items:center;gap:10px;padding:8px;background:rgba(0,212,255,0.05);border-radius:4px;border:1px solid rgba(0,212,255,0.2);">
          <img :src="fotoPreviewUrl" style="width:48px;height:48px;border-radius:4px;object-fit:cover;flex-shrink:0;">
          <div style="flex:1;min-width:0;">
            <p style="font-family:var(--font-body);font-size:12px;color:var(--color-primary);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="fotoFile?.name"></p>
            <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">Analisando base operacional...</p>
          </div>
          <button @click="removeFoto()" class="hov-icon-danger" style="padding:4px;color:var(--color-text-dim);background:transparent;border:none;cursor:pointer;transition:color 150ms;">
            <svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Resultados: Pessoas por texto -->
        <div x-show="searched && pessoasTexto.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Resultados por nome/CPF (<span x-text="pessoasTexto.length"></span>)
          </p>
          <template x-for="p in pessoasTexto.slice(0, 10)" :key="'t-' + p.id">
            <div @click="viewPessoa(p.id)"
                 class="hov-list-card"
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;">
              <!-- Avatar -->
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url" :alt="'Foto de ' + p.nome"
                     @click.stop="openPhotoModal(p.foto_principal_url, p.id, p)" style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);cursor:pointer;">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width:32px;height:32px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">
                  <svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <div style="flex:1;min-width:0;">
                <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);" x-text="p.nome"></p>
                <p x-show="p.cpf_masked" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'CPF: ' + p.cpf_masked"></p>
                <p x-show="p.apelido" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Vulgo: ' + p.apelido"></p>
                <p x-show="p.nome_mae" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Mãe: ' + p.nome_mae"></p>
              </div>
              <svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
              </svg>
            </div>
          </template>
          <button x-show="pessoasTexto.length > 10" @click="abrirVerMaisTexto()"
                  style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.5rem 0; align-self: center;">
            Ver mais resultados
          </button>
        </div>

        <!-- Resultados: Pessoas por foto -->
        <div x-show="pessoasFoto.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Resultados por foto (<span x-text="pessoasFoto.length"></span>)
          </p>
          <template x-for="r in pessoasFoto" :key="'f-' + r.foto_id">
            <div @click="r.pessoa_id && viewPessoa(r.pessoa_id)"
                 class="hov-list-card"
                 style="padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">
                  <img x-show="r.foto_principal_url || r.arquivo_url" :src="r.foto_principal_thumb_url || r.foto_principal_url || r.thumbnail_url || r.arquivo_url"
                       style="width:40px;height:40px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);">
                  <div style="flex:1;min-width:0;">
                    <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);" x-text="r.nome || 'Pessoa sem nome'"></p>
                    <p x-show="r.cpf_masked" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'CPF: ' + r.cpf_masked"></p>
                    <p x-show="r.apelido" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Vulgo: ' + r.apelido"></p>
                    <p x-show="r.nome_mae" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Mae: ' + r.nome_mae"></p>
                    <!-- Barra de confiança -->
                    <div style="margin-top:6px;display:flex;align-items:center;gap:8px;">
                      <div style="flex:1;height:4px;background:var(--color-surface-hover);border-radius:2px;overflow:hidden;">
                        <div style="height:100%;border-radius:2px;transition:all 300ms;"
                             :style="'width:' + Math.round(r.similaridade * 100) + '%;background:' + (r.similaridade >= 0.8 ? 'var(--color-success)' : r.similaridade >= 0.6 ? '#FFD700' : 'var(--color-danger)')">
                        </div>
                      </div>
                      <span style="font-family:var(--font-data);font-size:12px;font-weight:700;flex-shrink:0;"
                            :style="'color:' + (r.similaridade >= 0.8 ? 'var(--color-success)' : r.similaridade >= 0.6 ? '#FFD700' : 'var(--color-danger)')"
                            x-text="Math.round(r.similaridade * 100) + '%'">
                      </span>
                    </div>
                  </div>
                </div>
                <svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;margin-left:8px;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados por foto -->
        <p x-show="fotoSearchDone && !loadingPessoa && fotoServicoIndisponivel"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);text-transform:uppercase;letter-spacing:0.05em;">
          Reconhecimento facial indisponível neste servidor.
        </p>
        <p x-show="fotoSearchDone && !loadingPessoa && !fotoServicoIndisponivel && pessoasFoto.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhuma correspondência facial encontrada.
        </p>

        <!-- Sem resultados pessoa -->
        <div x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0 && !fotoSearchDone">
          <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Nenhuma pessoa encontrada. </span>
          <button @click="showCadastroPessoa = true; cpCarregarEstados(); if (query && !/^\\d/.test(query)) novaPessoa.nome = query; else if (query) novaPessoa.cpf = query"
                  style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-primary);background:transparent;border:none;cursor:pointer;">
            Cadastrar
          </button>
        </div>

        <!-- Formulario: cadastrar nova pessoa -->
        <div x-show="showCadastroPessoa" x-cloak
             style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:16px;display:flex;flex-direction:column;gap:12px;margin-top:4px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text);text-transform:uppercase;letter-spacing:0.06em;">Cadastrar Pessoa</h3>
            <button @click="showCadastroPessoa = false; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', nome_mae: '', endereco: '' }; this.cpEstadoId=null; this.cpCidadeId=null; this.cpCidadeTexto=''; this.cpBairroId=null; this.cpBairroTexto=''; fotoPessoa = null; fotoPessoaPreviewUrl = ''; erroCadastro = null; cpfCadastroErro = ''"
                    style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);background:transparent;border:none;cursor:pointer;">Cancelar</button>
          </div>

          <div>
            <label class="login-field-label">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo">
          </div>

          <div>
            <label class="login-field-label">CPF</label>
            <input type="text" :value="novaPessoa.cpf"
                   @input="novaPessoa.cpf = formatarCPF($event.target.value); cpfCadastroErro = novaPessoa.cpf.length === 14 && !validarCPF(novaPessoa.cpf) ? 'CPF inválido' : ''"
                   placeholder="000.000.000-00" maxlength="14" inputmode="numeric">
            <p x-show="cpfCadastroErro" x-text="cpfCadastroErro"
               style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);margin-top:4px;"></p>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div>
              <label class="login-field-label">Data de Nascimento</label>
              <input type="text" x-model="novaPessoa.data_nascimento"
                     @input="novaPessoa.data_nascimento = formatarData($event.target.value)"
                     placeholder="DD/MM/AAAA" maxlength="10">
            </div>
            <div>
              <label class="login-field-label">Vulgo</label>
              <input type="text" x-model="novaPessoa.apelido" placeholder="Apelido">
            </div>
          </div>

          <div>
            <label class="login-field-label">Nome da mãe</label>
            <input type="text" x-model="novaPessoa.nome_mae" placeholder="Nome completo da mãe" maxlength="300">
          </div>

          <div>
            <label class="login-field-label">Endereço</label>
            <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e número">
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div>
              <label class="login-field-label">Estado (UF)</label>
              <select x-model="cpEstadoId"
                      @change="cpCidadeId=null;cpCidadeTexto='';cpBairroId=null;cpBairroTexto='';cpCidadeSugestoes=[];cpBairroSugestoes=[];cpBuscarCidades()"
                      style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px 14px;font-size:13px;color:var(--color-text);font-family:var(--font-body);box-sizing:border-box;">
                <option value="">Selecione...</option>
                <template x-for="est in cpEstados" :key="est.id">
                  <option :value="est.id" x-text="est.sigla + ' — ' + est.nome_exibicao"></option>
                </template>
              </select>
            </div>
            <div style="position:relative;">
              <label class="login-field-label">Cidade</label>
              <input type="text" x-model="cpCidadeTexto" :disabled="!cpEstadoId"
                     @focus="cpBuscarCidades()"
                     @input.debounce.300ms="cpBuscarCidades()"
                     @blur.debounce.200ms="cpCidadeSugestoes=[]"
                     placeholder="Cidade">
              <div x-show="cpCidadeSugestoes.length > 0 || cpCidadeCadastrarNovo"
                   style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
                <template x-for="cidade in cpCidadeSugestoes" :key="cidade.id">
                  <div @mousedown.prevent="cpSelecionarCidade(cidade)"
                       class="hov-row-surface"
                       style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                    <span x-text="cidade.nome_exibicao"></span>
                  </div>
                </template>
                <div x-show="cpCidadeCadastrarNovo" @mousedown.prevent="cpCadastrarCidade()"
                     class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-primary);border-top:1px solid var(--color-border);">
                  + Cadastrar "<span x-text="cpCidadeTexto"></span>"
                </div>
              </div>
            </div>
            <div style="position:relative;">
              <label class="login-field-label">Bairro</label>
              <input type="text" x-model="cpBairroTexto" :disabled="!cpCidadeId"
                     @focus="cpBuscarBairros()"
                     @input.debounce.300ms="cpBuscarBairros()"
                     @blur.debounce.200ms="cpBairroSugestoes=[]"
                     placeholder="Bairro">
              <div x-show="cpBairroSugestoes.length > 0 || cpBairroCadastrarNovo"
                   style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
                <template x-for="bairro in cpBairroSugestoes" :key="bairro.id">
                  <div @mousedown.prevent="cpSelecionarBairro(bairro)"
                       class="hov-row-surface"
                       style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                    <span x-text="bairro.nome_exibicao"></span>
                  </div>
                </template>
                <div x-show="cpBairroCadastrarNovo" @mousedown.prevent="cpCadastrarBairro()"
                     class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-primary);border-top:1px solid var(--color-border);">
                  + Cadastrar "<span x-text="cpBairroTexto"></span>"
                </div>
              </div>
            </div>
          </div>

          <div>
            <label class="login-field-label">Foto</label>
            <label style="cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:var(--font-data);font-size:11px;padding:6px 12px;border-radius:4px;background:var(--color-surface-hover);color:var(--color-primary);border:1px solid var(--color-border);transition:all 150ms;">
              Selecionar foto
              <input type="file" accept="image/*"
                     @change="if (fotoPessoaPreviewUrl) URL.revokeObjectURL(fotoPessoaPreviewUrl); fotoPessoa = $event.target.files[0] || null; fotoPessoaPreviewUrl = fotoPessoa ? URL.createObjectURL(fotoPessoa) : ''"
                     class="hidden">
            </label>
            <template x-if="fotoPessoa">
              <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
                <img :src="fotoPessoaPreviewUrl" style="width:48px;height:48px;border-radius:4px;object-fit:cover;flex-shrink:0;">
                <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="fotoPessoa?.name"></span>
              </div>
            </template>
          </div>

          <button @click="criarPessoa()" class="btn btn-primary"
                  :disabled="salvandoPessoa || !novaPessoa.nome.trim() || !!cpfCadastroErro">
            <span x-show="!salvandoPessoa">SALVAR PESSOA</span>
            <span x-show="salvandoPessoa" style="display:flex;align-items:center;justify-content:center;gap:8px;">
              <span class="spinner"></span> SALVANDO...
            </span>
          </button>
          <p x-show="erroCadastro" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="erroCadastro"></p>
        </div>

        <!-- Spinner pessoa -->
        <div x-show="loadingPessoa" style="display:flex;flex-direction:column;align-items:center;padding:12px 0;gap:8px;">
          <span class="spinner"></span>
          <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">Analisando base operacional...</span>
        </div>
      </div>

      <!-- Separador -->
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="flex:1;height:1px;background:var(--color-border);"></div>
        <span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span>
        <div style="flex:1;height:1px;background:var(--color-border);"></div>
      </div>

      <!-- Filtros por Endereco (cascade por id) -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;position:relative;z-index:30;">
        <div>
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Filtros por Endereço</span>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Selecione estado (e opcionalmente cidade/bairro) e clique em Filtrar.</p>
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;">
          <div>
            <label class="login-field-label">Estado (UF)</label>
            <select x-model="fEstadoId" @change="onFiltroEstadoChange()"
                    style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px 14px;font-size:13px;color:var(--color-text);font-family:var(--font-body);box-sizing:border-box;">
              <option value="">Selecione...</option>
              <template x-for="est in fEstados" :key="est.id">
                <option :value="est.id" x-text="est.sigla + ' — ' + est.nome_exibicao"></option>
              </template>
            </select>
          </div>

          <div style="position:relative;">
            <label class="login-field-label">Cidade (opcional)</label>
            <input type="text" x-model="fCidadeTexto" :disabled="!fEstadoId"
                   @focus="fBuscarCidades()" @input.debounce.300ms="onFiltroCidadeInput()"
                   @blur.debounce.200ms="fCidadeSugestoes=[]" placeholder="Cidade" style="padding:12px 14px;">
            <div x-show="fCidadeSugestoes.length > 0"
                 style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
              <template x-for="c in fCidadeSugestoes" :key="c.id">
                <div @mousedown.prevent="fSelecionarCidade(c)" class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                  <span x-text="c.nome_exibicao"></span>
                </div>
              </template>
            </div>
          </div>

          <div style="position:relative;">
            <label class="login-field-label">Bairro (opcional)</label>
            <input type="text" x-model="fBairroTexto" :disabled="!fCidadeId"
                   @focus="fBuscarBairros()" @input.debounce.300ms="onFiltroBairroInput()"
                   @blur.debounce.200ms="fBairroSugestoes=[]" placeholder="Bairro" style="padding:12px 14px;">
            <div x-show="fBairroSugestoes.length > 0"
                 style="position:absolute;z-index:100;width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;margin-top:2px;max-height:180px;overflow-y:auto;">
              <template x-for="b in fBairroSugestoes" :key="b.id">
                <div @mousedown.prevent="fSelecionarBairro(b)" class="hov-row-surface"
                     style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--color-text);">
                  <span x-text="b.nome_exibicao"></span>
                </div>
              </template>
            </div>
          </div>

          <button @click="searchPorEndereco()" :disabled="!fEstadoId || loadingEndereco"
                  class="btn btn-primary" style="width:100%;">
            <span x-show="!loadingEndereco">Filtrar</span>
            <span x-show="loadingEndereco">Filtrando...</span>
          </button>
        </div>

        <p x-show="searchedEndereco && !loadingEndereco && pessoasEndereco.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhuma pessoa encontrada para este filtro.
        </p>
      </div>

      <!-- Separador -->
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="flex:1;height:1px;background:var(--color-border);"></div>
        <span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span>
        <div style="flex:1;height:1px;background:var(--color-border);"></div>
      </div>

      <!-- Buscar por Veiculo -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <div>
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Buscar por Veículo</span>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Encontre o abordado pelo veículo com que foi visto.</p>
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;">
          <div>
            <label class="login-field-label">Placa</label>
            <input type="text" :value="filtroPlaca"
                   @input="filtroPlaca = formatarPlaca($event.target.value); onInputVeiculo()"
                   placeholder="ABC-1234..." maxlength="8"
                   style="padding:12px 14px;text-transform:uppercase;">
          </div>
          <div>
            <label class="login-field-label">Modelo</label>
            <input type="text" x-model="filtroModelo" @input="onInputVeiculo()"
                   placeholder="Modelo do veículo..." style="padding:12px 14px;">
          </div>
          <div x-show="filtroModelo.length > 0">
            <label class="login-field-label">Cor <span style="color:var(--color-text-dim);">(opcional)</span></label>
            <select x-model="corDropdown" @change="onCorChangeVeiculo()"
                    style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px 14px;font-size:13px;color:var(--color-text);font-family:var(--font-body);box-sizing:border-box;">
              <option value="">Todas</option>
              <template x-for="c in coresVeiculo" :key="c"><option :value="c" x-text="c"></option></template>
              <option value="__outra__">Outra...</option>
            </select>
            <input x-show="corDropdown === '__outra__'" type="text" x-model="filtroCor" @input="onInputVeiculo()"
                   placeholder="Cor do veículo..." style="padding:12px 14px;margin-top:8px;">
          </div>
        </div>

        <!-- Resultados veiculo -->
        <div x-show="searchedVeiculo && pessoasVeiculo.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Abordados vinculados (<span x-text="pessoasVeiculo.length"></span>)
          </p>
          <template x-for="p in pessoasVeiculo.slice(0, 10)" :key="'v-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @click="viewPessoa(p.id)"
                 class="hov-list-card"
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url"
                     @click.stop="openPhotoModal(p.foto_principal_url, p.id, p)" style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);cursor:pointer;">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width:32px;height:32px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">
                  <svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <div style="flex:1;min-width:0;">
                <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);" x-text="p.nome"></p>
                <p x-show="p.cpf_masked" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'CPF: ' + p.cpf_masked"></p>
                <p x-show="p.apelido" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Vulgo: ' + p.apelido"></p>
                <p x-show="p.nome_mae" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Mãe: ' + p.nome_mae"></p>
                <p x-show="p.veiculo_info" style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;"
                   x-text="'Vinculado via: ' + [p.veiculo_info?.placa, p.veiculo_info?.modelo, p.veiculo_info?.cor, p.veiculo_info?.ano].filter(Boolean).join(' \u00b7 ')">
                </p>
              </div>
              <!-- Thumbnail veiculo -->
              <template x-if="p.veiculo_info?.foto_veiculo_url">
                <img :src="p.veiculo_info.foto_veiculo_url"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);">
              </template>
              <template x-if="!p.veiculo_info?.foto_veiculo_url">
                <div style="width:32px;height:32px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">
                  <svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>
                  </svg>
                </div>
              </template>
              <svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
              </svg>
            </div>
          </template>
          <button x-show="pessoasVeiculo.length > 10" @click="abrirVerMaisVeiculo()"
                  style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.5rem 0; align-self: center;">
            Ver mais resultados
          </button>
        </div>

        <p x-show="searchedVeiculo && !loadingVeiculo && pessoasVeiculo.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhum abordado vinculado a este veículo.
        </p>

        <div x-show="loadingVeiculo" style="display:flex;justify-content:center;padding:8px 0;">
          <span class="spinner"></span>
        </div>
      </div>

    <!-- Modal ver mais — busca por nome/CPF -->
    <div x-show="modalVerMaisTexto" x-cloak
         @click.self="modalVerMaisTexto = false"
         style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; overflow: hidden; display: flex; align-items: flex-start; justify-content: center; padding: 1rem;">
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 1rem; width: 100%; box-sizing: border-box; max-height: calc(100vh - 2rem); overflow-y: auto;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
          <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
            Resultados (<span x-text="pessoasTexto.length"></span>)
          </h3>
          <button @click="modalVerMaisTexto = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
        </div>
        <div x-show="loadingVerMais" style="display: flex; justify-content: center; padding: 1.5rem;">
          <span class="spinner"></span>
        </div>
        <div x-show="!loadingVerMais"><div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasTexto" :key="'mt-' + p.id">
            <div @click="if(p.foto_principal_url) openPhotoModal(p.foto_principal_url, p.id, p); else viewPessoa(p.id)"
                 style="cursor: pointer; text-align: center; min-width: 0;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width: 100%; aspect-ratio: 1; border-radius: 4px; background: var(--color-surface-hover); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim); border: 1px solid var(--color-border);">
                  <svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <p style="font-family: var(--font-data); font-size: 10px; color: var(--color-text); margin-top: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" x-text="p.nome"></p>
            </div>
          </template>
        </div></div>
      </div>
    </div>

    <!-- Modal ver mais — busca por endereço -->
    <div x-show="modalVerMaisEndereco" x-cloak
         @click.self="modalVerMaisEndereco = false"
         style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; overflow: hidden; display: flex; align-items: flex-start; justify-content: center; padding: 1rem;">
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 1rem; width: 100%; box-sizing: border-box; max-height: calc(100vh - 2rem); overflow-y: auto;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
          <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
            Resultados por endereço (<span x-text="pessoasEndereco.length"></span>)
          </h3>
          <button @click="modalVerMaisEndereco = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
        </div>
        <div x-show="loadingVerMais" style="display: flex; justify-content: center; padding: 1.5rem;">
          <span class="spinner"></span>
        </div>
        <div x-show="!loadingVerMais"><div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasEndereco" :key="'me-' + p.id">
            <div @click="if(p.foto_principal_url) openPhotoModal(p.foto_principal_url, p.id, p); else viewPessoa(p.id)"
                 style="cursor: pointer; text-align: center; min-width: 0;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width: 100%; aspect-ratio: 1; border-radius: 4px; background: var(--color-surface-hover); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim); border: 1px solid var(--color-border);">
                  <svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <p style="font-family: var(--font-data); font-size: 10px; color: var(--color-text); margin-top: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" x-text="p.nome"></p>
            </div>
          </template>
        </div></div>
      </div>
    </div>

    <!-- Modal ver mais — busca por veículo -->
    <div x-show="modalVerMaisVeiculo" x-cloak
         @click.self="modalVerMaisVeiculo = false"
         style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; overflow: hidden; display: flex; align-items: flex-start; justify-content: center; padding: 1rem;">
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 1rem; width: 100%; box-sizing: border-box; max-height: calc(100vh - 2rem); overflow-y: auto;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
          <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
            Abordados vinculados (<span x-text="pessoasVeiculo.length"></span>)
          </h3>
          <button @click="modalVerMaisVeiculo = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
        </div>
        <div x-show="loadingVerMais" style="display: flex; justify-content: center; padding: 1.5rem;">
          <span class="spinner"></span>
        </div>
        <div x-show="!loadingVerMais"><div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasVeiculo" :key="'mvv-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @click="if(p.foto_principal_url) openPhotoModal(p.foto_principal_url, p.id, p); else viewPessoa(p.id)"
                 style="cursor: pointer; text-align: center; min-width: 0;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_thumb_url || p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
              </template>
              <template x-if="!p.foto_principal_url">
                <div style="width: 100%; aspect-ratio: 1; border-radius: 4px; background: var(--color-surface-hover); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim); border: 1px solid var(--color-border);">
                  <svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                  </svg>
                </div>
              </template>
              <p style="font-family: var(--font-data); font-size: 10px; color: var(--color-text); margin-top: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" x-text="p.nome"></p>
            </div>
          </template>
        </div></div>
      </div>
    </div>

    ${personPhotoModalHTML()}
  </div>
  `;
}

// Estado preservado entre montagens do componente. Como a página é recriada do
// zero a cada navegação (renderPage faz innerHTML novo), guardamos aqui a busca
// e os resultados para restaurá-los quando o usuário volta da ficha de uma
// pessoa. Em entrada nova (pelo menu) o estado é descartado e a consulta abre
// limpa.
let _consultaPreservada = null;

/**
 * Componente Alpine.js da página de consulta.
 *
 * Gerencia estado de busca por texto, foto, endereço e veículo.
 * Inclui cadastro inline de nova pessoa. Toda lógica de busca
 * preservada da versão anterior.
 */
function consultaPage() {
  return {
    // Estado — busca pessoa por texto
    query: "",
    pessoasTexto: [],
    loadingPessoa: false,
    searched: false,
    buscouPessoa: false,
    _timerPessoa: null,

    // Estado — busca por foto
    fotoFile: null,
    fotoPreviewUrl: "",
    pessoasFoto: [],
    fotoSearchDone: false,
    fotoServicoIndisponivel: false,

    // Estado — endereco (cascade por id)
    fEstados: [],
    fEstadoId: "",
    fCidadeId: null,
    fCidadeTexto: "",
    fCidadeSugestoes: [],
    fBairroId: null,
    fBairroTexto: "",
    fBairroSugestoes: [],
    pessoasEndereco: [],
    loadingEndereco: false,
    searchedEndereco: false,

    // Estado — veiculo
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",
    // Dropdown de cor: lista fixa + opção "Outra" (texto livre)
    coresVeiculo: window.CORES_VEICULO || [],
    corDropdown: "",
    pessoasVeiculo: [],
    loadingVeiculo: false,
    searchedVeiculo: false,
    _timerVeiculo: null,

    // Estado — modais ver mais
    modalVerMaisTexto: false,
    modalVerMaisEndereco: false,
    modalVerMaisVeiculo: false,
    loadingVerMais: false,

    // Cadastro nova pessoa
    showCadastroPessoa: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", nome_mae: "", endereco: "" },
    fotoPessoa: null,
    fotoPessoaPreviewUrl: "",
    salvandoPessoa: false,
    erroCadastro: null,
    cpfBuscaErro: "",
    cpfCadastroErro: "",
    // Localidade cascata (cadastro pessoa)
    cpEstadoId: null,
    cpCidadeId: null,
    cpCidadeTexto: "",
    cpBairroId: null,
    cpBairroTexto: "",
    cpEstados: [],
    cpCidadeSugestoes: [],
    cpBairroSugestoes: [],
    cpCidadeCadastrarNovo: false,
    cpBairroCadastrarNovo: false,

    async init() {
      try {
        this.fEstados = await api.get("/localidades?tipo=estado");
      } catch {
        /* silencioso */
      }
      // Retorno via voltar (header/celular): restaura a busca que estava na tela.
      if (window.__argusNavDir === "back" && _consultaPreservada) {
        Object.assign(this, _consultaPreservada);
        return;
      }
      // Entrada nova (pelo menu): descarta o estado preservado.
      _consultaPreservada = null;
    },

    _isCPF(value) {
      return /^\d{3,}[\d.\-]*$/.test(value.trim());
    },

    onInputPessoa(value) {
      this.query = formatarBuscaQuery(value);
      if (this._isCPF(this.query)) {
        const digits = this.query.replace(/\D/g, "");
        if (digits.length === 11 && !validarCPF(this.query)) {
          this.cpfBuscaErro = "CPF inválido";
          this.pessoasTexto = [];
          this.searched = false;
          this.buscouPessoa = false;
          return;
        }
      }
      this.cpfBuscaErro = "";
      this.onInput();
    },

    onInput() {
      clearTimeout(this._timerPessoa);
      if (this.query.length < 2) {
        this.pessoasTexto = [];
        this.searched = false;
        this.buscouPessoa = false;
        return;
      }
      this._timerPessoa = setTimeout(() => this.searchPorTexto(), 400);
    },

    onFotoSelect(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      this.fotoFile = file;
      this.fotoPreviewUrl = URL.createObjectURL(file);
      this.searchPorFoto();
    },

    removeFoto() {
      if (this.fotoPreviewUrl) URL.revokeObjectURL(this.fotoPreviewUrl);
      this.fotoFile = null;
      this.fotoPreviewUrl = "";
      this.pessoasFoto = [];
      this.fotoSearchDone = false;
      this.fotoServicoIndisponivel = false;
      this.$refs.fotoInput.value = "";
      this.$refs.fotoInputCamera.value = "";
    },

    _limparResultadoEndereco() {
      this.pessoasEndereco = [];
      this.searchedEndereco = false;
    },

    onFiltroEstadoChange() {
      this.fCidadeId = null; this.fCidadeTexto = ""; this.fCidadeSugestoes = [];
      this.fBairroId = null; this.fBairroTexto = ""; this.fBairroSugestoes = [];
      this._limparResultadoEndereco();
    },

    onFiltroCidadeInput() {
      // Digitar invalida a seleção anterior (precisa re-selecionar para ter id).
      this.fCidadeId = null;
      this.fBairroId = null; this.fBairroTexto = ""; this.fBairroSugestoes = [];
      this._limparResultadoEndereco();
      this.fBuscarCidades();
    },

    onFiltroBairroInput() {
      this.fBairroId = null;
      this._limparResultadoEndereco();
      this.fBuscarBairros();
    },

    async fBuscarCidades() {
      if (!this.fEstadoId) { this.fCidadeSugestoes = []; return; }
      const q = this.fCidadeTexto.trim();
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=cidade&parent_id=${this.fEstadoId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=cidade&parent_id=${this.fEstadoId}`;
        this.fCidadeSugestoes = await api.get(url);
      } catch (e) { console.error(e); }
    },

    fSelecionarCidade(c) {
      this.fCidadeId = c.id; this.fCidadeTexto = c.nome_exibicao;
      this.fCidadeSugestoes = [];
      this.fBairroId = null; this.fBairroTexto = "";
      this._limparResultadoEndereco();
    },

    async fBuscarBairros() {
      if (!this.fCidadeId) { this.fBairroSugestoes = []; return; }
      const q = this.fBairroTexto.trim();
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=bairro&parent_id=${this.fCidadeId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=bairro&parent_id=${this.fCidadeId}`;
        this.fBairroSugestoes = await api.get(url);
      } catch (e) { console.error(e); }
    },

    fSelecionarBairro(b) {
      this.fBairroId = b.id; this.fBairroTexto = b.nome_exibicao;
      this.fBairroSugestoes = [];
      this._limparResultadoEndereco();
    },

    onCorChangeVeiculo() {
      // "Outra" libera campo de texto livre; demais opções filtram pela cor escolhida.
      this.filtroCor = this.corDropdown === "__outra__" ? "" : this.corDropdown;
      this.onInputVeiculo();
    },

    onInputVeiculo() {
      clearTimeout(this._timerVeiculo);
      const placaRaw = this.filtroPlaca.replace("-", "");
      const temFiltro = placaRaw.length >= 2 || this.filtroModelo.trim().length >= 2;
      if (!temFiltro) {
        this.pessoasVeiculo = [];
        this.searchedVeiculo = false;
        return;
      }
      this._timerVeiculo = setTimeout(() => this.searchPorVeiculo(), 400);
    },

    async searchPorTexto() {
      this.loadingPessoa = true;
      this.buscouPessoa = true;
      try {
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa&limit=200`;
        const r = await api.get(url);
        this.pessoasTexto = r.pessoas || [];
        this.searched = true;
      } catch {
        showToast("Erro na busca por nome/CPF", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorFoto() {
      if (!this.fotoFile) return;
      this.loadingPessoa = true;
      this.fotoSearchDone = false;
      this.fotoServicoIndisponivel = false;
      try {
        const r = await api.uploadFile("/fotos/buscar-rosto", this.fotoFile, { top_k: 5 });
        this.pessoasFoto = r.resultados || [];
        this.fotoServicoIndisponivel = r.disponivel === false;
        this.fotoSearchDone = true;
      } catch (err) {
        showToast(err?.message || "Erro na busca por foto", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorEndereco() {
      if (!this.fEstadoId) return;
      this.loadingEndereco = true;
      try {
        let url = `/consultas/?q=&tipo=pessoa&estado_id=${this.fEstadoId}`;
        if (this.fCidadeId) url += `&cidade_id=${this.fCidadeId}`;
        if (this.fBairroId) url += `&bairro_id=${this.fBairroId}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
        this.searchedEndereco = true;
        if (this.pessoasEndereco.length > 0) this.modalVerMaisEndereco = true;
      } catch {
        showToast("Erro no filtro por endereço", "error");
      } finally {
        this.loadingEndereco = false;
      }
    },

    async searchPorVeiculo() {
      this.loadingVeiculo = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.trim().length >= 2) params.append("modelo", this.filtroModelo.trim());
        if (this.filtroCor.trim().length >= 1) params.append("cor", this.filtroCor.trim());
        params.append("limit", "200");
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
        this.searchedVeiculo = true;
      } catch {
        showToast("Erro na busca por veiculo", "error");
      } finally {
        this.loadingVeiculo = false;
      }
    },

    async abrirVerMaisTexto() {
      this.modalVerMaisTexto = true;
      this.loadingVerMais = true;
      try {
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa&limit=200`;
        const r = await api.get(url);
        this.pessoasTexto = r.pessoas || [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    async abrirVerMaisVeiculo() {
      this.modalVerMaisVeiculo = true;
      this.loadingVerMais = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.trim().length >= 2) params.append("modelo", this.filtroModelo.trim());
        if (this.filtroCor.trim().length >= 1) params.append("cor", this.filtroCor.trim());
        params.append("limit", "200");
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        // Preserva a busca/resultados para restaurar ao voltar da ficha.
        _consultaPreservada = this._snapshotConsulta();
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].navigate("pessoa-detalhe");
      }
    },

    /**
     * Captura o estado de busca dos quatro modos (texto, foto, endereço,
     * veículo) para restaurar ao voltar da ficha de uma pessoa. Não inclui
     * modais, loadings nem o formulário de cadastro (transitórios).
     */
    _snapshotConsulta() {
      return {
        query: this.query,
        pessoasTexto: this.pessoasTexto,
        searched: this.searched,
        buscouPessoa: this.buscouPessoa,
        fotoFile: this.fotoFile,
        fotoPreviewUrl: this.fotoPreviewUrl,
        pessoasFoto: this.pessoasFoto,
        fotoSearchDone: this.fotoSearchDone,
        fotoServicoIndisponivel: this.fotoServicoIndisponivel,
        fEstadoId: this.fEstadoId,
        fCidadeId: this.fCidadeId,
        fCidadeTexto: this.fCidadeTexto,
        fBairroId: this.fBairroId,
        fBairroTexto: this.fBairroTexto,
        pessoasEndereco: this.pessoasEndereco,
        searchedEndereco: this.searchedEndereco,
        filtroPlaca: this.filtroPlaca,
        filtroModelo: this.filtroModelo,
        filtroCor: this.filtroCor,
        corDropdown: this.corDropdown,
        pessoasVeiculo: this.pessoasVeiculo,
        searchedVeiculo: this.searchedVeiculo,
      };
    },

    /**
     * Trata o "voltar" internamente: fecha o nível aberto (modal de foto, "ver
     * mais" ou cadastro) um por vez, do topo para a base. Chamado por
     * app.goBack(). Retorna true se fechou algo (permanece na página); false
     * para deixar o voltar sair da consulta.
     */
    interceptBack() {
      if (this.showPhotoModal) { this.closePhotoModal(); return true; }
      if (this.modalVerMaisTexto) { this.modalVerMaisTexto = false; return true; }
      if (this.modalVerMaisEndereco) { this.modalVerMaisEndereco = false; return true; }
      if (this.modalVerMaisVeiculo) { this.modalVerMaisVeiculo = false; return true; }
      if (this.showCadastroPessoa) { this.showCadastroPessoa = false; return true; }
      return false;
    },

    async cpCarregarEstados() {
      if (this.cpEstados.length > 0) return;
      try { this.cpEstados = await api.get('/localidades?tipo=estado'); } catch (e) { console.error(e); }
    },

    async cpBuscarCidades() {
      const q = this.cpCidadeTexto.trim();
      if (!this.cpEstadoId) { this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false; return; }
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}`;
        const r = await api.get(url);
        this.cpCidadeSugestoes = r;
        this.cpCidadeCadastrarNovo = q.length >= 1 && r.length === 0;
      } catch (e) { console.error(e); }
    },

    async cpBuscarBairros() {
      const q = this.cpBairroTexto.trim();
      if (!this.cpCidadeId) { this.cpBairroSugestoes = []; this.cpBairroCadastrarNovo = false; return; }
      try {
        const url = q.length >= 1
          ? `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}&q=${encodeURIComponent(q)}`
          : `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}`;
        const r = await api.get(url);
        this.cpBairroSugestoes = r;
        this.cpBairroCadastrarNovo = q.length >= 1 && r.length === 0;
      } catch (e) { console.error(e); }
    },

    cpSelecionarCidade(cidade) {
      this.cpCidadeId = cidade.id; this.cpCidadeTexto = cidade.nome_exibicao;
      this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false;
      this.cpBairroId = null; this.cpBairroTexto = '';
      this.cpBuscarBairros();
    },

    cpSelecionarBairro(bairro) {
      this.cpBairroId = bairro.id; this.cpBairroTexto = bairro.nome_exibicao;
      this.cpBairroSugestoes = []; this.cpBairroCadastrarNovo = false;
    },

    async cpCadastrarCidade() {
      const nome = this.cpCidadeTexto.trim();
      if (!nome || !this.cpEstadoId) return;
      try { this.cpSelecionarCidade(await api.post('/localidades', { nome, tipo: 'cidade', parent_id: parseInt(this.cpEstadoId) })); }
      catch (e) { showToast('Erro ao cadastrar cidade', 'error'); }
    },

    async cpCadastrarBairro() {
      const nome = this.cpBairroTexto.trim();
      if (!nome || !this.cpCidadeId) return;
      try { this.cpSelecionarBairro(await api.post('/localidades', { nome, tipo: 'bairro', parent_id: this.cpCidadeId })); }
      catch (e) { showToast('Erro ao cadastrar bairro', 'error'); }
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroCadastro = "Nome é obrigatório.";
        return;
      }

      if (this.novaPessoa.cpf.trim() && !validarCPF(this.novaPessoa.cpf)) {
        this.cpfCadastroErro = "CPF inválido";
        return;
      }

      this.salvandoPessoa = true;
      this.erroCadastro = null;

      try {
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) pessoaData.cpf = this.novaPessoa.cpf.trim();
        const dataNasc = parseDateBR(this.novaPessoa.data_nascimento);
        if (dataNasc) pessoaData.data_nascimento = dataNasc;
        if (this.novaPessoa.apelido.trim()) pessoaData.apelido = this.novaPessoa.apelido.trim();
        if (this.novaPessoa.nome_mae.trim()) pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();

        const pessoa = await api.post("/pessoas/", pessoaData);

        const temEndereco = this.novaPessoa.endereco.trim() || this.cpEstadoId || this.cpCidadeId;

        if (temEndereco) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            estado_id: this.cpEstadoId ? parseInt(this.cpEstadoId) : null,
            cidade_id: this.cpCidadeId || null,
            bairro_id: this.cpBairroId || null,
          });
        }

        if (this.fotoPessoa) {
          await api.uploadFile("/fotos/upload", this.fotoPessoa, {
            tipo: "rosto",
            pessoa_id: pessoa.id,
          });
        }

        this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", nome_mae: "", endereco: "" };
        this.cpfCadastroErro = "";
        this.cpfBuscaErro = "";
        this.cpEstadoId = null; this.cpCidadeId = null; this.cpCidadeTexto = ""; this.cpBairroId = null; this.cpBairroTexto = "";
        this.fotoPessoa = null;
        this.fotoPessoaPreviewUrl = "";
        this.showCadastroPessoa = false;
        showToast("Pessoa cadastrada com sucesso!", "success");
        this.viewPessoa(pessoa.id);
      } catch (err) {
        this.erroCadastro = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },
  };
}
