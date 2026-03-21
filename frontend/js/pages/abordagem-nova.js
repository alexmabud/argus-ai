/**
 * Página de nova abordagem — Argus AI.
 *
 * Formulário completo para registro de abordagem com busca/cadastro
 * de pessoas como primeiro passo, GPS automático, autocomplete de
 * veículos, captura de foto, entrada por voz e envio offline.
 */
function renderAbordagemNova() {
  return `
    <div x-data="abordagemForm()" x-init="initForm()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Title -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.05em;margin:0;">NOVA ABORDAGEM</h2>
        <span style="font-family:var(--font-data);font-size:11px;font-weight:500;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">REGISTRO OPERACIONAL</span>
      </div>

      <!-- 1. Pessoas abordadas (primeiro campo) -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoas abordadas</span>

        <div x-data="autocompleteComponent('pessoa')" style="position:relative;">
          <input type="text" :value="query"
                 @input="query = formatarBuscaQuery($event.target.value); onInput()"
                 @focus="showDropdown = results.length > 0 || noResults"
                 placeholder="Buscar por nome ou CPF..." style="width:100%;">

          <!-- Dropdown resultados -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               style="position:absolute;z-index:20;width:100%;margin-top:4px;max-height:14rem;overflow-y:auto;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">

            <!-- Resultados encontrados -->
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('pessoa-selected', { selected: selected })"
                      style="width:100%;text-align:left;padding:8px 12px;font-family:var(--font-body);font-size:14px;color:var(--color-text);border:none;background:transparent;cursor:pointer;border-bottom:1px solid var(--color-border);"
                      onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background='transparent'">
                <span x-text="getLabel(item)"></span>
                <span x-show="item.cpf_masked" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);margin-left:8px;" x-text="item.cpf_masked"></span>
              </button>
            </template>

            <!-- Nenhum resultado -->
            <div x-show="noResults" style="padding:12px;font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);">
              <p>Nenhuma pessoa encontrada.</p>
              <button @click="showDropdown = false; $dispatch('abrir-cadastro-pessoa', { query: query })"
                      style="margin-top:8px;width:100%;text-align:left;color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                + Cadastrar novo abordado
              </button>
            </div>
          </div>

          <!-- Tags selecionados -->
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
            <template x-for="item in selected" :key="item.id">
              <span style="background:rgba(0,212,255,0.15);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);font-family:var(--font-data);font-size:12px;padding:4px 8px;border-radius:4px;display:flex;align-items:center;gap:4px;">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('pessoa-selected', { selected: selected })"
                        style="color:var(--color-primary);background:transparent;border:none;cursor:pointer;font-size:14px;line-height:1;">&times;</button>
              </span>
            </template>
          </div>
        </div>

        <!-- Botão para cadastrar sem buscar -->
        <button x-show="!showNovaPessoa" @click="showNovaPessoa = true"
                style="color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;text-align:left;">
          + Adicionar pessoa não cadastrada
        </button>

        <!-- Formulário inline: cadastrar nova pessoa -->
        <div x-show="showNovaPessoa" x-cloak style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:16px;display:flex;flex-direction:column;gap:12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <h3 style="font-family:var(--font-display);font-size:13px;font-weight:500;color:var(--color-text);margin:0;">Cadastrar novo abordado</h3>
            <button @click="showNovaPessoa = false; novaPessoa = {nome:'',cpf:'',data_nascimento:'',apelido:'',endereco:'',bairro:'',cidade:'',estado:''}"
                    style="color:var(--color-text-muted);background:transparent;border:none;cursor:pointer;font-family:var(--font-data);font-size:11px;">Cancelar</button>
          </div>

          <div>
            <label class="login-field-label">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo">
          </div>

          <div>
            <label class="login-field-label">CPF</label>
            <input type="text" :value="novaPessoa.cpf" @input="novaPessoa.cpf = formatarCPF($event.target.value)" placeholder="000.000.000-00" maxlength="14" inputmode="numeric">
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
              <label class="login-field-label">Data de nascimento</label>
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
            <label class="login-field-label">Endereço</label>
            <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e número">
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div>
              <label class="login-field-label">Bairro</label>
              <input type="text" list="lista-bairros-pessoa" x-model="novaPessoa.bairro" placeholder="Bairro">
            </div>
            <div>
              <label class="login-field-label">Cidade</label>
              <input type="text" list="lista-cidades-pessoa" x-model="novaPessoa.cidade" placeholder="Cidade">
            </div>
            <div>
              <label class="login-field-label">Estado (UF)</label>
              <input type="text" list="lista-estados-pessoa" x-model="novaPessoa.estado" placeholder="DF" maxlength="2" style="text-transform:uppercase;">
            </div>
          </div>

          <!-- Datalists para autocomplete de localização -->
          <datalist id="lista-bairros-pessoa">
            <template x-for="b in localidades.bairros" :key="b"><option :value="b"></option></template>
          </datalist>
          <datalist id="lista-cidades-pessoa">
            <template x-for="c in localidades.cidades" :key="c"><option :value="c"></option></template>
          </datalist>
          <datalist id="lista-estados-pessoa">
            <template x-for="e in localidades.estados" :key="e"><option :value="e"></option></template>
          </datalist>

          <button @click="criarPessoa()" class="btn btn-primary" :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
            <span x-show="!salvandoPessoa">Salvar e adicionar</span>
            <span x-show="salvandoPessoa" style="display:flex;align-items:center;gap:8px;">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroPessoa" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="erroPessoa"></p>
        </div>

        <!-- Info e ações por abordado selecionado -->
        <div x-show="pessoasSelecionadas.length > 0" style="border-top:1px solid var(--color-border);padding-top:12px;display:flex;flex-direction:column;gap:12px;">
          <template x-for="p in pessoasSelecionadas" :key="p.id">
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:8px;">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                <span style="font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" x-text="p.nome"></span>
                <label :for="'foto-p-' + p.id"
                       style="cursor:pointer;font-family:var(--font-data);font-size:11px;padding:4px 8px;border-radius:4px;display:flex;align-items:center;gap:4px;"
                       :style="fotosPessoas[p.id]
                         ? 'background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);'
                         : 'background:var(--color-surface-hover);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);'">
                  <span x-text="fotosPessoas[p.id] ? 'FOTO OK' : 'CAPTURAR FOTO'"></span>
                </label>
                <input type="file" accept="image/*" capture="environment"
                       :id="'foto-p-' + p.id" style="display:none;"
                       @change="fotosPessoas = {...fotosPessoas, [p.id]: $event.target.files[0]}">
              </div>

              <!-- Endereço atual (se houver) -->
              <div x-show="pessoaEnderecos[p.id]?.length > 0" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">
                <span style="color:var(--color-text-dim);">Endereço atual:</span>
                <span x-text="formatEndereco(pessoaEnderecos[p.id]?.[0])"></span>
              </div>

              <!-- Botão novo endereço -->
              <button x-show="!novoEnderecoAberto[p.id]" @click="novoEnderecoAberto = {...novoEnderecoAberto, [p.id]: true}"
                      style="color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;text-align:left;">
                + Cadastrar novo endereço
              </button>

              <!-- Mini-form novo endereço -->
              <div x-show="novoEnderecoAberto[p.id]" x-cloak style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:8px;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                  <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text);text-transform:uppercase;letter-spacing:0.05em;">Novo endereço</span>
                  <button @click="novoEnderecoAberto = {...novoEnderecoAberto, [p.id]: false}"
                          style="color:var(--color-text-muted);background:transparent;border:none;cursor:pointer;font-family:var(--font-data);font-size:11px;">Cancelar</button>
                </div>
                <input type="text" x-model="novoEnderecoData[p.id + '_endereco']" placeholder="Rua e número">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                  <input type="text" list="lista-bairros-pessoa" x-model="novoEnderecoData[p.id + '_bairro']" placeholder="Bairro">
                  <input type="text" list="lista-cidades-pessoa" x-model="novoEnderecoData[p.id + '_cidade']" placeholder="Cidade">
                  <input type="text" list="lista-estados-pessoa" x-model="novoEnderecoData[p.id + '_estado']" placeholder="UF" maxlength="2" style="text-transform:uppercase;">
                </div>
                <button @click="salvarNovoEndereco(p.id)" class="btn btn-primary" style="font-size:12px;padding:6px 0;"
                        :disabled="salvandoEndereco[p.id] || !novoEnderecoData[p.id + '_endereco']?.trim()">
                  <span x-show="!salvandoEndereco[p.id]">Salvar endereço</span>
                  <span x-show="salvandoEndereco[p.id]" style="display:flex;align-items:center;gap:4px;">
                    <span class="spinner"></span> Salvando...
                  </span>
                </button>
                <p x-show="erroEndereco[p.id]" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="erroEndereco[p.id]"></p>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 3. Localização da abordagem -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Localização da abordagem</span>
          <button @click="captureGPS()" :disabled="gpsLoading"
                  style="color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
            <span x-show="!gpsLoading">Atualizar GPS</span>
            <span x-show="gpsLoading">Obtendo...</span>
          </button>
        </div>
        <p x-show="endereco" style="font-family:var(--font-data);font-size:14px;color:var(--color-text-muted);" x-text="endereco"></p>
        <p x-show="!endereco && !gpsLoading && !gpsErro" style="font-family:var(--font-data);font-size:14px;color:var(--color-text-dim);">GPS não capturado</p>
        <p x-show="gpsErro" style="font-family:var(--font-data);font-size:13px;color:var(--color-warning, #f59e0b);" x-text="gpsErro"></p>
        <p x-show="latitude" style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);" x-text="latitude?.toFixed(6) + ', ' + longitude?.toFixed(6)"></p>
      </div>

      <!-- 4. Veículo envolvido na abordagem -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
        <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Veículo envolvido na abordagem</span>

        <div x-data="autocompleteComponent('veiculo')" style="position:relative;">
          <input type="text" :value="query" @input="query = formatarPlaca($event.target.value); onInput()"
                 @focus="showDropdown = results.length > 0 || noResults"
                 placeholder="Buscar por placa..." maxlength="8"
                 style="width:100%;">

          <!-- Dropdown resultados -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               style="position:absolute;z-index:20;width:100%;margin-top:4px;max-height:14rem;overflow-y:auto;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">

            <!-- Resultados encontrados -->
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('veiculo-selected', { selected: selected })"
                      style="width:100%;text-align:left;padding:8px 12px;font-family:var(--font-body);font-size:14px;color:var(--color-text);border:none;background:transparent;cursor:pointer;border-bottom:1px solid var(--color-border);"
                      onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background='transparent'"
                      x-text="getLabel(item)">
              </button>
            </template>

            <!-- Nenhum resultado -->
            <div x-show="noResults" style="padding:12px;font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);">
              <p>Nenhum veículo encontrado.</p>
              <button @click="showDropdown = false; $dispatch('abrir-cadastro-veiculo', { query: query })"
                      style="margin-top:8px;width:100%;text-align:left;color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;">
                + Cadastrar novo veículo
              </button>
            </div>
          </div>

          <!-- Tags selecionados -->
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
            <template x-for="item in selected" :key="item.id">
              <span style="background:rgba(0,255,136,0.15);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);font-family:var(--font-data);font-size:12px;padding:4px 8px;border-radius:4px;display:flex;align-items:center;gap:4px;">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('veiculo-selected', { selected: selected })"
                        style="color:var(--color-success);background:transparent;border:none;cursor:pointer;font-size:14px;line-height:1;">&times;</button>
              </span>
            </template>
          </div>
        </div>

        <!-- Vínculo veículo → abordado -->
        <div x-show="veiculosSelecionados.length > 0 && pessoasSelecionadas.length > 0"
             style="padding-top:4px;display:flex;flex-direction:column;gap:8px;">
          <template x-for="v in veiculosSelecionados" :key="v.id">
            <div style="border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:8px;transition:border-color 0.2s;"
                 :style="veiculoPorPessoa[v.id]
                   ? 'border:1px solid rgba(0,255,136,0.4);background:rgba(0,255,136,0.05);'
                   : 'border:1px solid rgba(255,107,0,0.4);background:rgba(255,107,0,0.05);'"
                 :id="'vinculo-' + v.id">

              <!-- Cabeçalho: placa + status -->
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <div>
                    <span style="font-family:var(--font-data);font-weight:700;font-size:16px;color:var(--color-text);"
                          x-text="formatarPlaca(v.placa || '')"></span>
                    <span x-show="v.modelo || v.cor"
                          style="display:block;font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);"
                          x-text="[v.modelo, v.cor].filter(Boolean).join(' — ')"></span>
                  </div>
                </div>
                <span x-show="veiculoPorPessoa[v.id]"
                      style="color:var(--color-success);font-family:var(--font-data);font-size:12px;font-weight:600;text-transform:uppercase;">vinculado</span>
                <span x-show="!veiculoPorPessoa[v.id]"
                      style="color:var(--color-danger);font-family:var(--font-data);font-size:11px;text-transform:uppercase;">sem vínculo</span>
              </div>

              <!-- Seleção do condutor -->
              <div>
                <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);margin-bottom:8px;">Quem estava no veículo?</p>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                  <template x-for="p in pessoasSelecionadas" :key="p.id">
                    <button type="button"
                            @click="veiculoPorPessoa = {...veiculoPorPessoa, [v.id]: veiculoPorPessoa[v.id] === p.id ? null : p.id}"
                            style="font-family:var(--font-data);font-size:13px;padding:8px 12px;border-radius:4px;cursor:pointer;transition:all 0.15s;"
                            :style="veiculoPorPessoa[v.id] === p.id
                              ? 'background:rgba(0,212,255,0.15);border:1px solid var(--color-primary);color:var(--color-primary);font-weight:600;'
                              : 'background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-text-muted);'">
                      <span x-text="p.nome"></span>
                    </button>
                  </template>
                </div>
              </div>

              <!-- Foto do veículo -->
              <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
                <label :for="'foto-v-' + v.id"
                       style="cursor:pointer;font-family:var(--font-data);font-size:11px;padding:4px 8px;border-radius:4px;display:flex;align-items:center;gap:4px;"
                       :style="fotosVeiculos[v.id]
                         ? 'background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);'
                         : 'background:var(--color-surface-hover);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);'">
                  <span x-text="fotosVeiculos[v.id] ? 'FOTO OK' : 'CAPTURAR FOTO'"></span>
                </label>
                <input type="file" accept="image/*" capture="environment"
                       :id="'foto-v-' + v.id" style="display:none;"
                       @change="fotosVeiculos = {...fotosVeiculos, [v.id]: $event.target.files[0]}">
              </div>
            </div>
          </template>
        </div>

        <!-- Botão para cadastrar sem buscar -->
        <button x-show="!showNovoVeiculo" @click="showNovoVeiculo = true"
                style="color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;cursor:pointer;text-transform:uppercase;letter-spacing:0.05em;text-align:left;">
          + Adicionar veículo não cadastrado
        </button>

        <!-- Formulário inline: cadastrar novo veículo -->
        <div x-show="showNovoVeiculo" x-cloak style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:16px;display:flex;flex-direction:column;gap:12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <h3 style="font-family:var(--font-display);font-size:13px;font-weight:500;color:var(--color-text);margin:0;">Cadastrar novo veículo</h3>
            <button @click="showNovoVeiculo = false; novoVeiculo = {placa:'',modelo:'',cor:'',ano:''}"
                    style="color:var(--color-text-muted);background:transparent;border:none;cursor:pointer;font-family:var(--font-data);font-size:11px;">Cancelar</button>
          </div>

          <!-- Placa + Foto -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
              <label class="login-field-label">Placa *</label>
              <input type="text" :value="novoVeiculo.placa"
                     @input="novoVeiculo.placa = formatarPlaca($event.target.value)"
                     placeholder="ABC-1234" maxlength="8" style="text-transform:uppercase;">
            </div>
            <div>
              <label class="login-field-label">Foto do veículo</label>
              <input type="file" accept="image/*" capture="environment"
                     @change="onFotoVeiculoSelected($event)"
                     style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">
              <p x-show="fotoVeiculoFile" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:4px;" x-text="fotoVeiculoFile?.name"></p>
            </div>
          </div>

          <!-- Modelo + Cor + Ano -->
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div>
              <label class="login-field-label">Modelo</label>
              <input type="text" list="lista-modelos-veiculo" x-model="novoVeiculo.modelo" placeholder="Ex: Gol">
            </div>
            <div>
              <label class="login-field-label">Cor</label>
              <input type="text" list="lista-cores-veiculo" x-model="novoVeiculo.cor" placeholder="Ex: Branco">
            </div>
            <div>
              <label class="login-field-label">Ano</label>
              <input type="number" x-model="novoVeiculo.ano" placeholder="2020" min="1900" max="2100">
            </div>
          </div>

          <!-- Datalists para autocomplete de veículo -->
          <datalist id="lista-modelos-veiculo">
            <template x-for="m in veiculoLocalidades.modelos" :key="m"><option :value="m"></option></template>
          </datalist>
          <datalist id="lista-cores-veiculo">
            <template x-for="c in veiculoLocalidades.cores" :key="c"><option :value="c"></option></template>
          </datalist>

          <button @click="criarVeiculo()" class="btn btn-primary" :disabled="salvandoVeiculo || !novoVeiculo.placa.trim()">
            <span x-show="!salvandoVeiculo">Salvar e adicionar</span>
            <span x-show="salvandoVeiculo" style="display:flex;align-items:center;gap:8px;">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroVeiculo" style="font-family:var(--font-data);font-size:11px;color:var(--color-danger);" x-text="erroVeiculo"></p>
        </div>
      </div>

      <!-- 5. Observação -->
      <div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
          <label class="login-field-label" style="margin-bottom:0;">Observação</label>
          <button x-show="voiceSupported" @click="toggleVoice()"
                  style="font-family:var(--font-data);font-size:11px;padding:4px 10px;border-radius:4px;cursor:pointer;border:none;transition:all 0.15s;"
                  :style="recording
                    ? 'background:rgba(255,107,0,0.2);color:var(--color-danger);border:1px solid rgba(255,107,0,0.4);box-shadow:0 0 8px rgba(255,107,0,0.3);'
                    : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'">
            <span x-text="recording ? 'PARAR' : 'VOZ'"></span>
          </button>
        </div>
        <textarea x-model="observacao" rows="3" placeholder="Descreva a abordagem..."></textarea>
      </div>

      <!-- 6. Submit -->
      <div style="display:flex;flex-direction:column;gap:12px;padding-top:8px;">
        <button @click="submit()" class="btn btn-primary" :disabled="submitting">
          <span x-show="!submitting">Registrar Abordagem</span>
          <span x-show="submitting" style="display:flex;align-items:center;gap:8px;">
            <span class="spinner"></span> Salvando...
          </span>
        </button>

        <p x-show="erro" style="font-family:var(--font-data);font-size:13px;color:var(--color-danger);" x-text="erro"></p>
      </div>

      <!-- Modal de sucesso -->
      <div x-cloak
           role="dialog" aria-modal="true" aria-labelledby="modal-sucesso-titulo"
           :style="showSuccessModal ? 'display:flex;position:fixed;inset:0;z-index:50;background:rgba(5,10,15,0.85);align-items:center;justify-content:center;padding:0 16px;' : 'display:none;'">
        <div class="glass-card" style="padding:24px;border-radius:4px;max-width:384px;width:100%;display:flex;flex-direction:column;gap:20px;border:1px solid rgba(0,212,255,0.3);box-shadow:0 0 20px rgba(0,212,255,0.1);">

          <!-- Ícone de check -->
          <div style="display:flex;justify-content:center;">
            <div style="width:56px;height:56px;border-radius:4px;background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.3);display:flex;align-items:center;justify-content:center;">
              <svg style="width:32px;height:32px;color:var(--color-success);" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <!-- Título e mensagem -->
          <div style="text-align:center;display:flex;flex-direction:column;gap:4px;">
            <h3 id="modal-sucesso-titulo" style="font-family:var(--font-display);font-size:16px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.05em;margin:0;">Abordagem registrada!</h3>
            <p style="font-family:var(--font-data);font-size:13px;color:var(--color-text-muted);" x-text="successMessage"></p>
          </div>

          <!-- Ações -->
          <div style="display:flex;flex-direction:column;gap:8px;padding-top:4px;">
            <button @click="document.querySelector('[x-data]')._x_dataStack[0].navigate('abordagem-nova')"
                    class="btn btn-primary" style="width:100%;">
              Registrar nova abordagem
            </button>
            <button @click="document.querySelector('[x-data]')._x_dataStack[0].navigate('home')"
                    class="btn btn-secondary" style="width:100%;">
              Ir para página inicial
            </button>
          </div>

        </div>
      </div>
    </div>
  `;
}

function abordagemForm() {
  return {
    // GPS
    latitude: null,
    longitude: null,
    endereco: "",
    gpsLoading: false,
    gpsErro: null,

    // Formulário
    observacao: "",
    pessoaIds: [],
    pessoasSelecionadas: [],
    fotosPessoas: {},
    veiculoIds: [],
    veiculosSelecionados: [],
    veiculoPorPessoa: {},
    fotosVeiculos: {},   // { [veiculo_id]: File } — uma foto por veículo
    fotoVeiculoFile: null,   // arquivo temporário do form inline (limpo após salvar veículo)
    submitting: false,
    clientId: null,
    erro: null,
    // Modal de sucesso
    showSuccessModal: false,
    abordagemId: null,
    successMessage: null,

    // Voz
    recording: false,
    voiceSupported: typeof webkitSpeechRecognition !== "undefined" || typeof SpeechRecognition !== "undefined",

    // Cadastro nova pessoa
    showNovaPessoa: false,
    novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" },
    salvandoPessoa: false,
    erroPessoa: null,

    // Cadastro novo veículo
    showNovoVeiculo: false,
    novoVeiculo: { placa: "", modelo: "", cor: "", ano: "" },
    salvandoVeiculo: false,
    erroVeiculo: null,

    // Endereço de pessoa existente
    pessoaEnderecos: {},
    novoEnderecoAberto: {},
    novoEnderecoData: {},
    salvandoEndereco: {},
    erroEndereco: {},

    // Autocomplete de localidades (endereço pessoa)
    localidades: { bairros: [], cidades: [], estados: [] },

    // Autocomplete de localidades (veículo)
    veiculoLocalidades: { modelos: [], cores: [] },

    async initForm() {
      // Auto-capturar GPS apenas se permissão já foi concedida.
      // Se "prompt" (ainda não decidida), aguarda gesto do usuário para evitar
      // que o dialog apareça em momento inesperado e seja negado acidentalmente.
      if (navigator.permissions) {
        try {
          const perm = await navigator.permissions.query({ name: "geolocation" });
          if (perm.state === "granted") this.captureGPS();
        } catch {
          this.captureGPS(); // permissions API não suportada — tenta normalmente
        }
      } else {
        this.captureGPS();
      }

      // Carregar localidades para autocomplete
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch { /* silencioso — datalists ficam vazios */ }
      try {
        this.veiculoLocalidades = await api.get("/veiculos/localidades");
      } catch { /* silencioso */ }

      // Escutar seleções de autocomplete
      this.$el.addEventListener("pessoa-selected", (e) => {
        this.pessoaIds = e.detail.selected.map((s) => s.id);
        this.pessoasSelecionadas = e.detail.selected;
        // Buscar endereços das pessoas selecionadas
        for (const p of e.detail.selected) {
          if (!this.pessoaEnderecos[p.id]) {
            this.carregarEnderecos(p.id);
          }
        }
      });
      this.$el.addEventListener("veiculo-selected", (e) => {
        this.veiculoIds = e.detail.selected.map((s) => s.id);
        this.veiculosSelecionados = e.detail.selected;
      });

      // Escutar pedido de abrir cadastro de veículo (vindo do autocomplete)
      this.$el.addEventListener("abrir-cadastro-veiculo", (e) => {
        this.showNovoVeiculo = true;
        const q = e.detail?.query || "";
        if (q) this.novoVeiculo.placa = q;
      });

      // Escutar pedido de abrir cadastro (vindo do autocomplete)
      this.$el.addEventListener("abrir-cadastro-pessoa", (e) => {
        const q = e.detail?.query || "";
        // Criar novo objeto para garantir reatividade no Alpine.js
        if (q && /^\d/.test(q)) {
          this.novaPessoa = { nome: "", cpf: q, data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
        } else {
          this.novaPessoa = { nome: q, cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
        }
        this.showNovaPessoa = true;
      });
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroPessoa = "Nome é obrigatório.";
        return;
      }

      this.salvandoPessoa = true;
      this.erroPessoa = null;

      try {
        // Criar pessoa
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) {
          pessoaData.cpf = this.novaPessoa.cpf.trim();
        }
        const dataNasc = parseDateBR(this.novaPessoa.data_nascimento);
        if (dataNasc) {
          pessoaData.data_nascimento = dataNasc;
        }
        if (this.novaPessoa.apelido.trim()) {
          pessoaData.apelido = this.novaPessoa.apelido.trim();
        }

        const pessoa = await api.post("/pessoas/", pessoaData);

        // Criar endereço se preenchido
        if (this.novaPessoa.endereco.trim() || this.novaPessoa.bairro.trim() || this.novaPessoa.cidade.trim() || this.novaPessoa.estado.trim()) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim() || "-",
            bairro: this.novaPessoa.bairro.trim() || null,
            cidade: this.novaPessoa.cidade.trim() || null,
            estado: this.novaPessoa.estado.trim().toUpperCase() || null,
          });
        }

        // Adicionar à lista de abordados
        this.pessoaIds.push(pessoa.id);
        this.pessoasSelecionadas.push(pessoa);

        // Atualizar tags do autocomplete
        const autocompleteEl = this.$el.querySelector("[x-data*='autocompleteComponent']");
        if (autocompleteEl?._x_dataStack) {
          autocompleteEl._x_dataStack[0].selected.push(pessoa);
        }

        // Reset formulário
        this.novaPessoa = { nome: "", cpf: "", endereco: "", bairro: "", cidade: "", estado: "" };
        this.showNovaPessoa = false;
      } catch (err) {
        this.erroPessoa = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },

    async carregarEnderecos(pessoaId) {
      try {
        const detalhe = await api.get(`/pessoas/${pessoaId}`);
        this.pessoaEnderecos = { ...this.pessoaEnderecos, [pessoaId]: detalhe.enderecos || [] };
      } catch { /* silencioso */ }
    },

    async salvarNovoEndereco(pessoaId) {
      const endereco = this.novoEnderecoData[pessoaId + "_endereco"]?.trim();
      if (!endereco) return;

      this.salvandoEndereco = { ...this.salvandoEndereco, [pessoaId]: true };
      this.erroEndereco = { ...this.erroEndereco, [pessoaId]: null };

      try {
        await api.post(`/pessoas/${pessoaId}/enderecos`, {
          endereco: endereco,
          bairro: this.novoEnderecoData[pessoaId + "_bairro"]?.trim() || null,
          cidade: this.novoEnderecoData[pessoaId + "_cidade"]?.trim() || null,
          estado: this.novoEnderecoData[pessoaId + "_estado"]?.trim().toUpperCase() || null,
        });

        // Recarregar endereços e fechar form
        await this.carregarEnderecos(pessoaId);
        this.novoEnderecoAberto = { ...this.novoEnderecoAberto, [pessoaId]: false };
        this.novoEnderecoData = {
          ...this.novoEnderecoData,
          [pessoaId + "_endereco"]: "",
          [pessoaId + "_bairro"]: "",
          [pessoaId + "_cidade"]: "",
          [pessoaId + "_estado"]: "",
        };
      } catch (err) {
        this.erroEndereco = { ...this.erroEndereco, [pessoaId]: err.message || "Erro ao salvar endereço." };
      } finally {
        this.salvandoEndereco = { ...this.salvandoEndereco, [pessoaId]: false };
      }
    },

    formatEndereco(end) {
      if (!end) return "";
      const parts = [end.endereco, end.bairro, end.cidade, end.estado].filter(Boolean);
      return parts.join(", ");
    },

    async criarVeiculo() {
      const placa = this.novoVeiculo.placa.trim();
      if (!placa) {
        this.erroVeiculo = "Placa é obrigatória.";
        return;
      }

      this.salvandoVeiculo = true;
      this.erroVeiculo = null;

      try {
        const veiculoData = { placa };
        if (this.novoVeiculo.modelo.trim()) veiculoData.modelo = this.novoVeiculo.modelo.trim();
        if (this.novoVeiculo.cor.trim()) veiculoData.cor = this.novoVeiculo.cor.trim();
        if (this.novoVeiculo.ano) veiculoData.ano = parseInt(this.novoVeiculo.ano);

        const veiculo = await api.post("/veiculos/", veiculoData);

        // Adicionar à lista de veículos da abordagem
        this.veiculoIds.push(veiculo.id);
        this.veiculosSelecionados.push(veiculo);

        // Atualizar tags do autocomplete de veículo (segundo autocomplete na seção)
        const veiculoAutoEl = this.$el.querySelectorAll("[x-data*='autocompleteComponent']")[1];
        if (veiculoAutoEl?._x_dataStack) {
          veiculoAutoEl._x_dataStack[0].selected.push(veiculo);
        }

        // Guardar foto do veículo novo indexada pelo ID
        if (this.fotoVeiculoFile) {
          this.fotosVeiculos = { ...this.fotosVeiculos, [veiculo.id]: this.fotoVeiculoFile };
          this.fotoVeiculoFile = null;
        }

        this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
        this.showNovoVeiculo = false;
      } catch (err) {
        this.erroVeiculo = err.message || "Erro ao cadastrar veículo.";
      } finally {
        this.salvandoVeiculo = false;
      }
    },

    async captureGPS() {
      this.gpsLoading = true;
      this.gpsErro = null;

      try {
        const loc = await getGPSLocation();
        this.latitude = loc.latitude;
        this.longitude = loc.longitude;
        this.endereco = loc.endereco_texto || "";
      } catch (err) {
        // Se TIMEOUT com high accuracy, tenta novamente com low accuracy
        if (err && err.code === 3) {
          try {
            const loc = await getGPSLocationLowAccuracy();
            this.latitude = loc.latitude;
            this.longitude = loc.longitude;
            this.endereco = loc.endereco_texto || "";
            return;
          } catch { /* fallback também falhou */ }
        }
        this.endereco = "";
        if (err && err.code === 1) {
          this.gpsErro = "GPS bloqueado. Clique no cadeado (🔒) na barra de endereços → Localização → Permitir. No Windows, verifique também: Configurações → Privacidade → Localização → Ativar.";
        } else if (err && err.code === 2) {
          this.gpsErro = "Sinal de GPS indisponível.";
        } else if (err && err.code === 3) {
          this.gpsErro = "Tempo esgotado ao capturar GPS.";
        } else {
          this.gpsErro = "GPS não suportado neste dispositivo.";
        }
      } finally {
        this.gpsLoading = false;
      }
    },

    toggleVoice() {
      if (this.recording) {
        stopVoice();
        this.recording = false;
      } else {
        startVoice(
          (text, isFinal) => {
            if (isFinal) {
              this.observacao += (this.observacao ? " " : "") + text;
            }
          },
          () => { this.recording = false; }
        );
        this.recording = true;
      }
    },

    onFotoVeiculoSelected(event) {
      this.fotoVeiculoFile = event.target.files[0] || null;
    },

    async submit() {
      if (this.submitting) return;

      // Validar que todo veículo está vinculado a um abordado
      for (const v of this.veiculosSelecionados) {
        if (!this.veiculoPorPessoa[v.id]) {
          const placa = formatarPlaca(v.placa || "");
          this.erro = `Vincule o veículo ${placa} a um dos abordados antes de registrar.`;
          const cardEl = document.getElementById(`vinculo-${v.id}`);
          if (cardEl) cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }
      }

      this.submitting = true;
      this.erro = null;

      // Gerar client_id único para deduplicação (idempotência)
      if (!this.clientId) {
        this.clientId = crypto.randomUUID();
      }

      const obsTexto = this.observacao || "";

      const payload = {
        data_hora: new Date().toISOString(),
        latitude: this.latitude,
        longitude: this.longitude,
        endereco_texto: this.endereco || null,
        observacao: obsTexto || null,
        origem: navigator.onLine ? "online" : "offline",
        client_id: this.clientId,
        pessoa_ids: this.pessoaIds,
        veiculo_ids: this.veiculoIds,
        veiculo_por_pessoa: Object.fromEntries(
          Object.entries(this.veiculoPorPessoa).filter(([, v]) => v !== null)
        ),
        passagens: [],
      };

      try {
        if (navigator.onLine) {
          const result = await api.post("/abordagens/", payload);

          // Upload foto de cada abordado
          for (const [pessoaId, file] of Object.entries(this.fotosPessoas)) {
            if (file) {
              await api.uploadFile("/fotos/upload", file, {
                tipo: "rosto",
                pessoa_id: parseInt(pessoaId),
                abordagem_id: result.id,
              });
            }
          }

          // Upload foto de cada veículo com seu veiculo_id
          for (const [veiculoIdStr, file] of Object.entries(this.fotosVeiculos)) {
            if (file) {
              await api.uploadFile("/fotos/upload", file, {
                tipo: "veiculo",
                abordagem_id: result.id,
                veiculo_id: parseInt(veiculoIdStr),
              });
            }
          }

          this.abordagemId = result.id;
          this.successMessage = `Abordagem #${result.id} registrada com sucesso.`;
          // Capturar dados antes do reset para o modal
          this.resetForm();
          this.showSuccessModal = true;
        } else {
          // Salvar offline
          await enqueueSync("abordagem", payload);
          // Atualizar contador de pendentes
          const appEl = document.querySelector("[x-data]");
          if (appEl?._x_dataStack) appEl._x_dataStack[0]._updateSyncCount();
          this.abordagemId = null;
          this.successMessage = "Abordagem salva na fila offline. Será sincronizada automaticamente.";
          this.resetForm();
          this.showSuccessModal = true;
        }
      } catch (err) {
        this.erro = err.message || "Erro ao registrar abordagem.";
      } finally {
        this.submitting = false;
      }
    },

    resetForm() {
      this.clientId = null;
      this.observacao = "";
      this.pessoaIds = [];
      this.pessoasSelecionadas = [];
      this.fotosPessoas = {};
      this.pessoaEnderecos = {};
      this.novoEnderecoAberto = {};
      this.novoEnderecoData = {};
      this.veiculoIds = [];
      this.veiculosSelecionados = [];
      this.veiculoPorPessoa = {};
      this.fotosVeiculos = {};
      this.fotoVeiculoFile = null;
      this.showNovaPessoa = false;
      this.showNovoVeiculo = false;
      this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
      this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
      this.salvandoEndereco = {};
      this.erroEndereco = {};
      this.erroPessoa = null;
      this.erroVeiculo = null;
      this.erro = null;
      this.abordagemId = null;
      this.successMessage = null;
    },
  };
}
