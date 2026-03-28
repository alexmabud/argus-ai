/**
 * Pagina de consulta unificada — Argus AI.
 *
 * Secoes independentes: busca de pessoa (nome/CPF ou foto),
 * filtros por endereco e busca por veiculo. Cada secao retorna
 * a ficha do abordado como resultado. Estetica cyberpunk tatica.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header da pagina -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.08em;">
          Consulta Operacional
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">
          Busca Integrada // Pessoa / Endereco / Veiculo
        </p>
      </div>

      <!-- Pessoa -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoa</span>
          <button @click="showCadastroPessoa = !showCadastroPessoa; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; fotoPessoa = null; fotoPessoaPreviewUrl = ''; erroCadastro = null"
                  style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-primary);background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
            + Nova Pessoa
          </button>
        </div>

        <!-- Campo texto -->
        <div style="position:relative;">
          <input type="text" :value="query"
                 @input="query = formatarBuscaQuery($event.target.value); onInput()"
                 placeholder="NOME COMPLETO OU CPF..."
                 inputmode="text"
                 style="padding-left:40px;">
          <svg style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--color-text-dim);width:18px;height:18px;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>

        <!-- Separador -->
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="flex:1;height:1px;background:var(--color-border);"></div>
          <span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span>
          <div style="flex:1;height:1px;background:var(--color-border);"></div>
        </div>

        <!-- Reconhecimento Facial -->
        <button x-show="!fotoFile" @click="$refs.fotoInput.click()"
                style="width:100%;display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 12px;border-radius:4px;border:2px dashed rgba(0,212,255,0.3);background:rgba(0,212,255,0.03);cursor:pointer;transition:all 150ms;"
                onmouseover="this.style.background='rgba(0,212,255,0.06)';this.style.borderColor='rgba(0,212,255,0.5)'"
                onmouseout="this.style.background='rgba(0,212,255,0.03)';this.style.borderColor='rgba(0,212,255,0.3)'">
          <div style="width:40px;height:40px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;color:var(--color-primary);">
            <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/>
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/>
            </svg>
          </div>
          <div style="text-align:center;">
            <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-primary);">Reconhecimento Facial</p>
            <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Toque para enviar foto e comparar com o banco</p>
          </div>
        </button>
        <input type="file" x-ref="fotoInput" accept="image/jpeg,image/png,image/webp"
               class="hidden" @change="onFotoSelect($event)">

        <!-- Preview da foto -->
        <div x-show="fotoFile" style="display:flex;align-items:center;gap:10px;padding:8px;background:rgba(0,212,255,0.05);border-radius:4px;border:1px solid rgba(0,212,255,0.2);">
          <img :src="fotoPreviewUrl" style="width:48px;height:48px;border-radius:4px;object-fit:cover;flex-shrink:0;">
          <div style="flex:1;min-width:0;">
            <p style="font-family:var(--font-body);font-size:12px;color:var(--color-primary);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" x-text="fotoFile?.name"></p>
            <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">Analisando base operacional...</p>
          </div>
          <button @click="removeFoto()" style="padding:4px;color:var(--color-text-dim);background:transparent;border:none;cursor:pointer;transition:color 150ms;"
                  onmouseover="this.style.color='var(--color-danger)'" onmouseout="this.style.color='var(--color-text-dim)'">
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
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;"
                 onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.boxShadow='0 0 8px rgba(0,212,255,0.08)'"
                 onmouseout="this.style.borderColor='var(--color-border)';this.style.boxShadow='none'">
              <!-- Avatar -->
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" :alt="'Foto de ' + p.nome"
                     @pointerdown.stop="iniciarZoom(p.foto_principal_url)" @pointerup.stop="cancelarZoom()" @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);touch-action:manipulation;">
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
              </div>
              <svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
              </svg>
            </div>
          </template>
          <button x-show="pessoasTexto.length > 10" @click="abrirVerMaisTexto()"
                  style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.5rem 0; align-self: center;">
            Ver mais resultados (<span x-text="pessoasTexto.length"></span> total)
          </button>
        </div>

        <!-- Resultados: Pessoas por foto -->
        <div x-show="pessoasFoto.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Resultados por foto (<span x-text="pessoasFoto.length"></span>)
          </p>
          <template x-for="r in pessoasFoto" :key="'f-' + r.foto_id">
            <div @click="r.pessoa_id && viewPessoa(r.pessoa_id)"
                 style="padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;"
                 onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.boxShadow='0 0 8px rgba(0,212,255,0.08)'"
                 onmouseout="this.style.borderColor='var(--color-border)';this.style.boxShadow='none'">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">
                  <img x-show="r.foto_principal_url || r.arquivo_url" :src="r.foto_principal_url || r.arquivo_url"
                       style="width:40px;height:40px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);">
                  <div style="flex:1;min-width:0;">
                    <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);" x-text="r.nome || 'Pessoa sem nome'"></p>
                    <p x-show="r.cpf_masked" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'CPF: ' + r.cpf_masked"></p>
                    <p x-show="r.apelido" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Vulgo: ' + r.apelido"></p>
                    <!-- Barra de confianca -->
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
          Reconhecimento facial indisponivel neste servidor.
        </p>
        <p x-show="fotoSearchDone && !loadingPessoa && !fotoServicoIndisponivel && pessoasFoto.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhuma correspondencia facial encontrada.
        </p>

        <!-- Sem resultados pessoa -->
        <div x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0 && !fotoSearchDone">
          <span style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Nenhuma pessoa encontrada. </span>
          <button @click="showCadastroPessoa = true; if (query && !/^\\d/.test(query)) novaPessoa.nome = query; else if (query) novaPessoa.cpf = query"
                  style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-primary);background:transparent;border:none;cursor:pointer;">
            Cadastrar
          </button>
        </div>

        <!-- Formulario: cadastrar nova pessoa -->
        <div x-show="showCadastroPessoa" x-cloak
             style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:16px;display:flex;flex-direction:column;gap:12px;margin-top:4px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text);text-transform:uppercase;letter-spacing:0.06em;">Cadastrar Pessoa</h3>
            <button @click="showCadastroPessoa = false; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; fotoPessoa = null; fotoPessoaPreviewUrl = ''; erroCadastro = null"
                    style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);background:transparent;border:none;cursor:pointer;">Cancelar</button>
          </div>

          <div>
            <label class="login-field-label">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo">
          </div>

          <div>
            <label class="login-field-label">CPF</label>
            <input type="text" :value="novaPessoa.cpf"
                   @input="novaPessoa.cpf = formatarCPF($event.target.value)"
                   placeholder="000.000.000-00" maxlength="14" inputmode="numeric">
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
            <label class="login-field-label">Endereco</label>
            <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e numero">
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 80px;gap:8px;">
            <div>
              <label class="login-field-label">Bairro</label>
              <input type="text" list="lista-bairros-c" x-model="novaPessoa.bairro" placeholder="Bairro">
            </div>
            <div>
              <label class="login-field-label">Cidade</label>
              <input type="text" list="lista-cidades-c" x-model="novaPessoa.cidade" placeholder="Cidade">
            </div>
            <div>
              <label class="login-field-label">UF</label>
              <input type="text" list="lista-estados-c" x-model="novaPessoa.estado" placeholder="DF" maxlength="2" style="text-transform:uppercase;">
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
                  :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
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

      <!-- Filtros por Endereco -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <div>
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Filtros por Endereco</span>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Filtre abordados pelo local de residencia cadastrado.</p>
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;">
          <div>
            <label class="login-field-label">Bairro</label>
            <input type="text" list="lista-bairros-c" x-model="filtroBairro" @input="onInputEndereco()"
                   placeholder="Bairro..." style="padding:12px 14px;">
          </div>
          <div>
            <label class="login-field-label">Cidade</label>
            <input type="text" list="lista-cidades-c" x-model="filtroCidade" @input="onInputEndereco()"
                   placeholder="Cidade..." style="padding:12px 14px;">
          </div>
          <div>
            <label class="login-field-label">Estado (UF)</label>
            <input type="text" list="lista-estados-c" x-model="filtroEstado" @input="onInputEndereco()"
                   placeholder="DF" maxlength="2" style="padding:12px 14px;text-transform:uppercase;">
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

        <!-- Resultados por endereco -->
        <div x-show="searchedEndereco && pessoasEndereco.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Pessoas neste endereco (<span x-text="pessoasEndereco.length"></span>)
          </p>
          <template x-for="p in pessoasEndereco.slice(0, 10)" :key="'e-' + p.id">
            <div @click="viewPessoa(p.id)"
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;"
                 onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.boxShadow='0 0 8px rgba(0,212,255,0.08)'"
                 onmouseout="this.style.borderColor='var(--color-border)';this.style.boxShadow='none'">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url"
                     @pointerdown.stop="iniciarZoom(p.foto_principal_url)" @pointerup.stop="cancelarZoom()" @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);touch-action:manipulation;">
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
                <p x-show="p.endereco_criado_em" style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);"
                   x-text="'Cadastrado em ' + new Date(p.endereco_criado_em).toLocaleDateString('pt-BR')"></p>
              </div>
              <svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
              </svg>
            </div>
          </template>
          <button x-show="pessoasEndereco.length > 10" @click="abrirVerMaisEndereco()"
                  style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.5rem 0; align-self: center;">
            Ver mais resultados (<span x-text="pessoasEndereco.length"></span> total)
          </button>
        </div>

        <p x-show="searchedEndereco && !loadingEndereco && pessoasEndereco.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhuma pessoa encontrada neste endereco.
        </p>

        <div x-show="loadingEndereco" style="display:flex;justify-content:center;padding:8px 0;">
          <span class="spinner"></span>
        </div>
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
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Buscar por Veiculo</span>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Encontre o abordado pelo veiculo com que foi visto.</p>
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
                   placeholder="Modelo do veiculo..." style="padding:12px 14px;">
          </div>
          <div x-show="filtroModelo.length > 0">
            <label class="login-field-label">Cor <span style="color:var(--color-text-dim);">(opcional)</span></label>
            <input type="text" x-model="filtroCor" @input="onInputVeiculo()"
                   placeholder="Cor do veiculo..." style="padding:12px 14px;">
          </div>
        </div>

        <!-- Resultados veiculo -->
        <div x-show="searchedVeiculo && pessoasVeiculo.length > 0" style="display:flex;flex-direction:column;gap:6px;">
          <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">
            Abordados vinculados (<span x-text="pessoasVeiculo.length"></span>)
          </p>
          <template x-for="p in pessoasVeiculo.slice(0, 10)" :key="'v-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @click="viewPessoa(p.id)"
                 style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;cursor:pointer;border:1px solid var(--color-border);background:var(--color-surface);transition:all 150ms;"
                 onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.boxShadow='0 0 8px rgba(0,212,255,0.08)'"
                 onmouseout="this.style.borderColor='var(--color-border)';this.style.boxShadow='none'">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url"
                     @pointerdown.stop="iniciarZoom(p.foto_principal_url)" @pointerup.stop="cancelarZoom()" @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);touch-action:manipulation;">
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
            Ver mais resultados (<span x-text="pessoasVeiculo.length"></span> total)
          </button>
        </div>

        <p x-show="searchedVeiculo && !loadingVeiculo && pessoasVeiculo.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">
          Nenhum abordado vinculado a este veiculo.
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
        <div x-show="!loadingVerMais" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasTexto" :key="'mt-' + p.id">
            <div @pointerdown.stop="iniciarZoom(p.foto_principal_url)"
                 @pointerup="if (!zoomFotoVisible) { cancelarZoom(); modalVerMaisTexto = false; viewPessoa(p.id); } else { cancelarZoom(); }"
                 @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: manipulation;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
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
        </div>
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
        <div x-show="!loadingVerMais" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasEndereco" :key="'me-' + p.id">
            <div @pointerdown.stop="iniciarZoom(p.foto_principal_url)"
                 @pointerup="if (!zoomFotoVisible) { cancelarZoom(); modalVerMaisEndereco = false; viewPessoa(p.id); } else { cancelarZoom(); }"
                 @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: manipulation;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
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
        </div>
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
        <div x-show="!loadingVerMais" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasVeiculo" :key="'mvv-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @pointerdown.stop="iniciarZoom(p.foto_principal_url)"
                 @pointerup="if (!zoomFotoVisible) { cancelarZoom(); modalVerMaisVeiculo = false; viewPessoa(p.id); } else { cancelarZoom(); }"
                 @pointerleave="cancelarZoom()" @pointercancel="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: manipulation;">
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; border: 1px solid var(--color-border); display: block;">
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
        </div>
      </div>
    </div>

    <!-- Overlay de zoom de foto -->
    <div x-show="zoomFotoVisible" @pointerdown.stop="cancelarZoom()"
         style="position:fixed;inset:0;z-index:100;background:rgba(0,0,0,0.92);display:flex;align-items:center;justify-content:center;touch-action:none;">
      <img :src="zoomFotoUrl" alt="Foto ampliada"
           style="max-width:80vw;max-height:80vh;border-radius:4px;object-fit:contain;pointer-events:none;">
    </div>
  </div>
  `;
}

/**
 * Componente Alpine.js da pagina de consulta.
 *
 * Gerencia estado de busca por texto, foto, endereco e veiculo.
 * Inclui cadastro inline de nova pessoa. Toda logica de busca
 * preservada da versao anterior.
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

    // Estado — endereco
    filtroBairro: "",
    filtroCidade: "",
    filtroEstado: "",
    pessoasEndereco: [],
    loadingEndereco: false,
    searchedEndereco: false,
    _timerEndereco: null,

    // Estado — veiculo
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",
    pessoasVeiculo: [],
    loadingVeiculo: false,
    searchedVeiculo: false,
    _timerVeiculo: null,

    // Estado — modais ver mais
    modalVerMaisTexto: false,
    modalVerMaisEndereco: false,
    modalVerMaisVeiculo: false,
    loadingVerMais: false,
    zoomFotoUrl: '',
    zoomFotoVisible: false,
    _zoomTimer: null,

    // Dados auxiliares
    localidades: { bairros: [], cidades: [], estados: [] },

    // Cadastro nova pessoa
    showCadastroPessoa: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" },
    fotoPessoa: null,
    fotoPessoaPreviewUrl: "",
    salvandoPessoa: false,
    erroCadastro: null,

    async init() {
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch {
        /* silencioso */
      }
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
    },

    onInputEndereco() {
      clearTimeout(this._timerEndereco);
      const temFiltro = this.filtroBairro.length >= 2 || this.filtroCidade.length >= 2 || this.filtroEstado.length >= 1;
      if (!temFiltro) {
        this.pessoasEndereco = [];
        this.searchedEndereco = false;
        return;
      }
      this._timerEndereco = setTimeout(() => this.searchPorEndereco(), 400);
    },

    onInputVeiculo() {
      clearTimeout(this._timerVeiculo);
      const placaRaw = this.filtroPlaca.replace("-", "");
      const temFiltro = placaRaw.length >= 2 || this.filtroModelo.length >= 2;
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
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`;
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
        const form = new FormData();
        form.append("file", this.fotoFile);
        form.append("top_k", "5");
        const r = await api.postForm("/fotos/buscar-rosto", form);
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
      this.loadingEndereco = true;
      try {
        let url = `/consultas/?q=&tipo=pessoa`;
        if (this.filtroBairro.length >= 2) url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
        if (this.filtroCidade.length >= 2) url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
        if (this.filtroEstado.length >= 1) url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
        this.searchedEndereco = true;
      } catch {
        showToast("Erro no filtro por endereco", "error");
      } finally {
        this.loadingEndereco = false;
      }
    },

    async searchPorVeiculo() {
      this.loadingVeiculo = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.length >= 2) params.append("modelo", this.filtroModelo);
        if (this.filtroCor.length >= 1) params.append("cor", this.filtroCor);
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
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa&limit=10000`;
        const r = await api.get(url);
        this.pessoasTexto = r.pessoas || [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    async abrirVerMaisEndereco() {
      this.modalVerMaisEndereco = true;
      this.loadingVerMais = true;
      try {
        let url = `/consultas/?q=&tipo=pessoa&limit=10000`;
        if (this.filtroBairro.length >= 2) url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
        if (this.filtroCidade.length >= 2) url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
        if (this.filtroEstado.length >= 1) url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
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
        if (this.filtroModelo.length >= 2) params.append("modelo", this.filtroModelo);
        if (this.filtroCor.length >= 1) params.append("cor", this.filtroCor);
        params.append("limit", "10000");
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    iniciarZoom(url) {
      if (!url) return;
      this._zoomTimer = setTimeout(() => {
        this.zoomFotoUrl = url;
        this.zoomFotoVisible = true;
      }, 200);
    },

    cancelarZoom() {
      clearTimeout(this._zoomTimer);
      this._zoomTimer = null;
      this.zoomFotoVisible = false;
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0].currentPage = "pessoa-detalhe";
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroCadastro = "Nome e obrigatorio.";
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

        const pessoa = await api.post("/pessoas/", pessoaData);

        const temEndereco = this.novaPessoa.endereco.trim()
          || this.novaPessoa.bairro.trim()
          || this.novaPessoa.cidade.trim()
          || this.novaPessoa.estado.trim();

        if (temEndereco) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            bairro: this.novaPessoa.bairro.trim() || null,
            cidade: this.novaPessoa.cidade.trim() || null,
            estado: this.novaPessoa.estado.trim().toUpperCase() || null,
          });
        }

        if (this.fotoPessoa) {
          await api.uploadFile("/fotos/upload", this.fotoPessoa, {
            tipo: "rosto",
            pessoa_id: pessoa.id,
          });
        }

        this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
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
