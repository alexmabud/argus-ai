/**
 * Página de detalhe de pessoa — Argus AI.
 *
 * Exibe dados pessoais, fotos, endereços, relacionamentos
 * (vínculos com outras pessoas), veículos e histórico de abordagens.
 * Todas as informações aparecem sem ocultação.
 */

function renderPessoaDetalhe(appState) {
  const pessoaId = appState._pessoaId;
  if (!pessoaId) {
    return `<p style="color: var(--color-text-muted)">Nenhuma pessoa selecionada.</p>`;
  }

  return `
    <div x-data="pessoaDetalhePage(${pessoaId})" x-init="load()" style="display: flex; flex-direction: column; gap: 1rem; padding-bottom: 6rem;">
      <!-- Loading -->
      <div x-show="loading" style="display: flex; justify-content: center; padding: 3rem 0;">
        <span class="spinner"></span>
      </div>

      <!-- Conteúdo -->
      <template x-if="pessoa && !loading">
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <!-- Header -->
          <div>
            <button @click="goBack()" style="color: var(--color-primary); font-family: var(--font-body); font-size: 0.875rem; background: none; border: none; cursor: pointer; margin-bottom: 0.5rem; display: block;">&larr; Voltar</button>
            <h2 x-text="pessoa.nome" style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0;"></h2>
            <p x-show="pessoa.apelido" x-text="'Vulgo: ' + pessoa.apelido" style="font-size: 0.875rem; color: var(--color-secondary); font-weight: 500; margin: 0.25rem 0 0 0;"></p>
          </div>

          <!-- Dados pessoais -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">Dados Pessoais</h3>
              <button @click="abrirModalEditarPessoa()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); padding: 0.125rem; transition: color 0.15s;"
                      onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                      title="Editar dados pessoais">
                <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/>
                </svg>
              </button>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.875rem;">
              <div>
                <span style="color: var(--color-text-dim)">CPF:</span>
                <span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="pessoa.cpf || pessoa.cpf_masked || '—'"></span>
              </div>
              <div>
                <span style="color: var(--color-text-dim)">Cadastro:</span>
                <span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="new Date(pessoa.criado_em).toLocaleDateString('pt-BR')"></span>
              </div>
              <div>
                <span style="color: var(--color-text-dim)">Nascimento:</span>
                <span style="color: var(--color-text-muted); margin-left: 0.25rem;"
                      x-text="formatarNascimento(pessoa.data_nascimento)"></span>
              </div>
              <div>
                <span style="color: var(--color-text-dim)">Abordagens:</span>
                <span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="pessoa.abordagens_count || 0"></span>
              </div>
            </div>
            <div x-show="pessoa.observacoes" style="padding-top: 0.25rem;">
              <span style="font-size: 0.75rem; color: var(--color-text-dim)">Obs:</span>
              <p style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;" x-text="pessoa.observacoes"></p>
            </div>
          </div>

          <!-- Fotos -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); flex: 1; margin-right: 0.5rem;">
                Fotos (<span x-text="fotos.length"></span>)
              </h3>
              <!-- Botões câmera + galeria -->
              <div style="display: flex; gap: 0.375rem;">
                <label style="cursor: pointer; font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: var(--color-surface-hover); color: var(--color-primary);">
                  📷
                  <input type="file" accept="image/*" capture="environment" style="display: none;"
                         @change="onNovaFotoSelected($event)">
                </label>
                <label style="cursor: pointer; font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: var(--color-surface-hover); color: var(--color-primary);">
                  📁
                  <input type="file" accept="image/*" style="display: none;"
                         @change="onNovaFotoSelected($event)">
                </label>
              </div>
            </div>

            <!-- Preview + botão enviar (aparece após selecionar) -->
            <template x-if="novaFotoFile">
              <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem; background: var(--color-surface-hover); border-radius: 4px;">
                <img :src="novaFotoPreviewUrl" style="width: 3rem; height: 3rem; border-radius: 4px; object-fit: cover; flex-shrink: 0;">
                <div style="flex: 1; min-width: 0;">
                  <p style="font-size: 0.75rem; color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0;" x-text="novaFotoFile?.name"></p>
                </div>
                <div style="display: flex; gap: 0.375rem; flex-shrink: 0;">
                  <button @click="uploadNovaFoto()"
                          :disabled="uploadandoFoto"
                          style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: var(--color-success); color: var(--color-bg); border: none; cursor: pointer; opacity: 1;"
                          :style="uploadandoFoto ? 'opacity: 0.5' : ''">
                    <span x-show="!uploadandoFoto">Enviar</span>
                    <span x-show="uploadandoFoto" class="spinner"></span>
                  </button>
                  <button @click="cancelarNovaFoto()"
                          style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: var(--color-surface); color: var(--color-text-muted); border: 1px solid var(--color-border); cursor: pointer;">
                    ✕
                  </button>
                </div>
              </div>
            </template>

            <!-- Grid de fotos existentes -->
            <div x-show="fotos.length > 0">
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
              <template x-for="foto in fotos.slice(0, 4)" :key="foto.id">
                <div style="position: relative;">
                  <img :src="foto.arquivo_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; display: block;" loading="lazy"
                       @click="fotoAmpliada = foto.arquivo_url">
                  <span style="position: absolute; bottom: 0.125rem; left: 0.125rem; background: rgba(5,10,15,0.75); font-size: 9px; color: var(--color-text-muted); padding: 0 0.2rem; border-radius: 2px;"
                        x-text="foto.tipo || 'foto'"></span>
                </div>
              </template>
              </div>
            </div>

            <button x-show="fotos.length > 4" @click="modalTodasFotos = true"
                    style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.25rem 0; align-self: flex-start;">
              Ver mais (<span x-text="fotos.length - 4"></span>)
            </button>

            <!-- Estado vazio -->
            <p x-show="fotos.length === 0 && !novaFotoFile" style="font-size: 0.75rem; color: var(--color-text-dim); margin: 0;">
              Nenhuma foto cadastrada.
            </p>
          </div>

          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem;">
            <div @click.stop style="display: flex; flex-direction: column; max-width: min(90vw, 480px); width: 100%;">
              <img :src="fotoAmpliada" @click="fotoAmpliada = null"
                   style="width: 100%; border-radius: 4px 4px 0 0; display: block; cursor: pointer; object-fit: contain; max-height: 70vh;">
              <div style="background: rgba(5,10,15,0.95); border-radius: 0 0 4px 4px; padding: 0.75rem;">
                <p x-show="pessoa?.nome"
                   style="font-family: var(--font-display); font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0 0 0.375rem 0; font-size: 1rem;" x-text="pessoa?.nome"></p>
                <p x-show="pessoa?.apelido"
                   style="font-size: 0.8rem; color: var(--color-secondary); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'Vulgo: ' + pessoa?.apelido"></p>
                <p x-show="pessoa?.data_nascimento"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'Nasc: ' + formatarNascimento(pessoa?.data_nascimento, '')"></p>
                <p x-show="pessoa?.cpf || pessoa?.cpf_masked"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'CPF: ' + (pessoa?.cpf || pessoa?.cpf_masked)"></p>
                <p x-show="pessoa?.enderecos?.length > 0"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0;"
                   x-text="'End: ' + formatEndereco(pessoa?.enderecos?.[0])"></p>
              </div>
            </div>
          </div>

          <!-- Modal todas as fotos -->
          <div x-show="modalTodasFotos" x-cloak
               @click.self="modalTodasFotos = false"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 45; display: flex; align-items: flex-start; justify-content: center; padding: 1rem; overflow-y: auto;">
            <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 1rem; width: 100%; max-width: 32rem;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                  Fotos de <span x-text="pessoa.nome"></span> (<span x-text="fotos.length"></span>)
                </h3>
                <button @click="modalTodasFotos = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
                <template x-for="foto in fotos" :key="'modal-' + foto.id">
                  <div style="position: relative;">
                    <img :src="foto.arquivo_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; display: block;" loading="lazy"
                         @click="fotoAmpliada = foto.arquivo_url">
                    <span style="position: absolute; bottom: 0.125rem; left: 0.125rem; background: rgba(5,10,15,0.75); font-size: 9px; color: var(--color-text-muted); padding: 0 0.2rem; border-radius: 2px;"
                          x-text="foto.tipo || 'foto'"></span>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Modal todas fotos de veículo -->
          <div x-show="modalFotosVeiculo" x-cloak
               @click.self="modalFotosVeiculo = null"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 45; display: flex; align-items: flex-start; justify-content: center; padding: 1rem; overflow-y: auto;">
            <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 1rem; width: 100%; max-width: 32rem;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                  Fotos do Veículo (<span x-text="fotosVeiculos[modalFotosVeiculo]?.length || 0"></span>)
                </h3>
                <button @click="modalFotosVeiculo = null" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
                <template x-for="fv in (fotosVeiculos[modalFotosVeiculo] || [])" :key="'mv-' + fv.id">
                  <img :src="fv.arquivo_url" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; display: block;" loading="lazy"
                       @click="fotoAmpliada = fv.arquivo_url">
                </template>
              </div>
            </div>
          </div>

          <!-- Modal editar dados pessoais -->
          <div x-cloak
               @click.self="modalEditarPessoa = false"
               :style="modalEditarPessoa ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.7);z-index:50;align-items:center;justify-content:center;padding:1rem;' : 'display:none;'">
            <div class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 0.75rem;"
                 @click.stop>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;">Editar Dados Pessoais</h3>
                <button @click="modalEditarPessoa = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Nome <span style="color: var(--color-danger)">*</span></label>
                  <input type="text" x-model="editPessoaForm.nome"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">CPF</label>
                  <input type="text" x-model="editPessoaForm.cpf"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Data de Nascimento</label>
                  <input type="text" x-model="editPessoaForm.data_nascimento"
                         @input="editPessoaForm.data_nascimento = formatarData($event.target.value)"
                         placeholder="DD/MM/AAAA" maxlength="10"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Apelido</label>
                  <input type="text" x-model="editPessoaForm.apelido"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Observações</label>
                  <textarea x-model="editPessoaForm.observacoes" rows="2"
                            style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); resize: none; box-sizing: border-box;"
                            onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'"></textarea>
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem; padding-top: 0.25rem;">
                <button @click="modalEditarPessoa = false"
                        style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                <button @click="salvarEditPessoa()"
                        :disabled="!editPessoaForm.nome.trim() || salvandoPessoa"
                        class="btn btn-primary"
                        style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">
                  <span x-show="!salvandoPessoa">Salvar</span>
                  <span x-show="salvandoPessoa" class="spinner"></span>
                </button>
              </div>
            </div>
          </div>

          <!-- Modal editar/criar endereço -->
          <div x-cloak
               @click.self="modalEditarEndereco = false"
               :style="modalEditarEndereco ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.7);z-index:50;align-items:center;justify-content:center;padding:1rem;' : 'display:none;'">
            <div class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 0.75rem;"
                 @click.stop>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;"
                    x-text="modoEndereco === 'editar' ? 'Editar Endereço' : 'Novo Endereço'"></h3>
                <button @click="modalEditarEndereco = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Logradouro <span style="color: var(--color-danger)">*</span></label>
                  <input type="text" x-model="editEnderecoForm.endereco"
                         placeholder="Rua, número..."
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <!-- Estado -->
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Estado (UF)</label>
                  <select x-model="enderecoEstadoId"
                          @change="enderecoCidadeId=null; enderecoCidadeTexto=''; enderecoBairroId=null; enderecoBairroTexto=''; enderecoCidadeSugestoes=[]; enderecoBairroSugestoes=[];"
                          style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                    <option value="">Selecione o estado...</option>
                    <template x-for="est in enderecoEstados" :key="est.id">
                      <option :value="est.id" x-text="est.sigla + ' — ' + est.nome_exibicao"></option>
                    </template>
                  </select>
                </div>

                <!-- Cidade -->
                <div style="position: relative;">
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Cidade</label>
                  <input type="text"
                         x-model="enderecoCidadeTexto"
                         :disabled="!enderecoEstadoId"
                         @input.debounce.400ms="buscarCidades()"
                         @blur.debounce.200ms="enderecoCidadeSugestoes = []"
                         placeholder="Digite para buscar..."
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                  <div x-show="enderecoCidadeSugestoes.length > 0 || enderecoCidadeCadastrarNovo"
                       style="position: absolute; z-index: 100; width: 100%; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-top: 2px; max-height: 200px; overflow-y: auto;">
                    <template x-for="cidade in enderecoCidadeSugestoes" :key="cidade.id">
                      <div @mousedown.prevent="selecionarCidade(cidade)"
                           style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-text);"
                           onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
                        <span x-text="cidade.nome_exibicao"></span>
                      </div>
                    </template>
                    <div x-show="enderecoCidadeCadastrarNovo"
                         @mousedown.prevent="cadastrarNovaCidade()"
                         style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-primary); border-top: 1px solid var(--color-border);"
                         onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
                      + Cadastrar "<span x-text="enderecoCidadeTexto"></span>" como nova cidade
                    </div>
                  </div>
                </div>

                <!-- Bairro -->
                <div style="position: relative;">
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Bairro</label>
                  <input type="text"
                         x-model="enderecoBairroTexto"
                         :disabled="!enderecoCidadeId"
                         @input.debounce.400ms="buscarBairros()"
                         @blur.debounce.200ms="enderecoBairroSugestoes = []"
                         placeholder="Digite para buscar..."
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                  <div x-show="enderecoBairroSugestoes.length > 0 || enderecoBairroCadastrarNovo"
                       style="position: absolute; z-index: 100; width: 100%; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-top: 2px; max-height: 200px; overflow-y: auto;">
                    <template x-for="bairro in enderecoBairroSugestoes" :key="bairro.id">
                      <div @mousedown.prevent="selecionarBairro(bairro)"
                           style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-text);"
                           onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
                        <span x-text="bairro.nome_exibicao"></span>
                      </div>
                    </template>
                    <div x-show="enderecoBairroCadastrarNovo"
                         @mousedown.prevent="cadastrarNovoBairro()"
                         style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-primary); border-top: 1px solid var(--color-border);"
                         onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
                      + Cadastrar "<span x-text="enderecoBairroTexto"></span>" como novo bairro
                    </div>
                  </div>
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem; padding-top: 0.25rem;">
                <button @click="modalEditarEndereco = false"
                        style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                <button @click="salvarEditEndereco()"
                        :disabled="!editEnderecoForm.endereco.trim() || salvandoEndereco"
                        class="btn btn-primary"
                        style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">
                  <span x-show="!salvandoEndereco">Salvar</span>
                  <span x-show="salvandoEndereco" class="spinner"></span>
                </button>
              </div>
            </div>
          </div>

          <!-- Modal preview de pessoa coabordada -->
          <div x-show="pessoaPreview" x-cloak
               @click.self="pessoaPreview = null"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.7); z-index: 50; display: flex; align-items: flex-end; justify-content: center; padding: 1rem;">
            <div @click="viewPessoa(pessoaPreview.id)"
                 class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 0.75rem; cursor: pointer;">
              <!-- Foto ou ícone -->
              <div style="display: flex; justify-content: center;">
                <template x-if="pessoaPreview?.foto_principal_url">
                  <img :src="pessoaPreview.foto_principal_url"
                       style="width: 5rem; height: 5rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border);">
                </template>
                <template x-if="!pessoaPreview?.foto_principal_url">
                  <div style="width: 5rem; height: 5rem; border-radius: 4px; background: var(--color-surface-hover); border: 2px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim);">
                    <svg style="width: 2.5rem; height: 2.5rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                    </svg>
                  </div>
                </template>
              </div>
              <!-- Dados -->
              <div style="text-align: center; display: flex; flex-direction: column; gap: 0.25rem;">
                <p style="font-size: 1rem; font-weight: 700; color: var(--color-text); font-family: var(--font-display); text-transform: uppercase; margin: 0;" x-text="pessoaPreview?.nome"></p>
                <p x-show="pessoaPreview?.apelido"
                   style="font-size: 0.875rem; color: var(--color-secondary); font-weight: 500; margin: 0;"
                   x-text="'Vulgo: ' + pessoaPreview?.apelido"></p>
                <p x-show="pessoaPreview?.cpf_masked"
                   style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"
                   x-text="'CPF: ' + pessoaPreview?.cpf_masked"></p>
                <p x-show="pessoaPreview?.data_nascimento"
                   style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"
                   x-text="'Nascimento: ' + formatarNascimento(pessoaPreview?.data_nascimento, '')"></p>
              </div>
              <!-- Botão -->
              <div style="padding-top: 0.25rem;">
                <div style="width: 100%; text-align: center; font-size: 0.875rem; font-weight: 600; color: var(--color-primary); padding: 0.5rem; border-radius: 4px; border: 1px solid rgba(0,212,255,0.3); background: rgba(0,212,255,0.08); font-family: var(--font-data); text-transform: uppercase; letter-spacing: 0.05em;">
                  Ver ficha completa →
                </div>
              </div>
            </div>
          </div>

          <!-- Modal de criar/editar observação -->
          <div x-show="modalObservacao" x-cloak @click.self="modalObservacao = false"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem;">
            <div class="glass-card" style="width: 100%; max-width: 480px; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; position: relative;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-data); font-size: 0.875rem; font-weight: 700; color: var(--color-text); margin: 0; text-transform: uppercase; letter-spacing: 0.05em;"
                    x-text="obsForm.id ? 'Editar Observação' : 'Nova Observação'"></h3>
                <button @click="modalObservacao = false"
                        style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); font-size: 1.25rem; line-height: 1;">×</button>
              </div>

              <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-dim); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">
                  Observação <span style="color: var(--color-danger)">*</span>
                </label>
                <textarea x-model="obsForm.texto" rows="4"
                          placeholder="Digite a observação..."
                          style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.625rem; color: var(--color-text); font-size: 0.875rem; font-family: var(--font-data); resize: vertical; outline: none;"
                          @focus="$el.style.borderColor='var(--color-primary)'"
                          @blur="$el.style.borderColor='var(--color-border)'"></textarea>
              </div>

              <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button @click="modalObservacao = false"
                        style="padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border); border-radius: 4px; color: var(--color-text-dim); cursor: pointer; font-size: 0.8125rem; font-family: var(--font-data);">
                  Cancelar
                </button>
                <button @click="salvarObservacao()" :disabled="salvandoObs || !obsForm.texto.trim()"
                        style="padding: 0.5rem 1rem; background: var(--color-primary); border: none; border-radius: 4px; color: #000; font-weight: 700; cursor: pointer; font-size: 0.8125rem; font-family: var(--font-data); opacity: 1; transition: opacity 0.15s;"
                        :style="(salvandoObs || !obsForm.texto.trim()) ? 'opacity: 0.5; cursor: not-allowed;' : ''">
                  <span x-show="!salvandoObs" x-text="obsForm.id ? 'Salvar' : 'Adicionar'"></span>
                  <span x-show="salvandoObs">Salvando...</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Modal de cadastro de vínculo manual -->
          <div x-cloak
               @click.self="fecharModalVinculo()"
               :style="modalVinculo ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.7);z-index:50;align-items:center;justify-content:center;padding:1rem;' : 'display:none;'">
            <div class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 1rem;"
                 @click.stop>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;">Cadastrar Vínculo Manual</h3>
                <button @click="fecharModalVinculo()" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>

              <!-- Busca de pessoa -->
              <div x-show="!pessoaSelecionada && !subFormNovaPessoa">
                <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Buscar pessoa</label>
                <input type="text"
                       x-model="buscaVinculo"
                       @input="onBuscaVinculo()"
                       placeholder="Nome, apelido ou CPF..."
                       style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                       onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">

                <!-- Loading -->
                <div x-show="buscandoPessoa" style="display: flex; justify-content: center; padding: 0.5rem 0;">
                  <span class="spinner"></span>
                </div>

                <!-- Resultados -->
                <div x-show="resultadosBusca.length > 0 || (buscaVinculo.trim().length >= 2 && !buscandoPessoa)"
                     style="margin-top: 0.25rem; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; overflow: hidden;">
                  <template x-for="p in resultadosBusca" :key="p.id">
                    <div @click="selecionarPessoa(p)"
                         style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--color-border); cursor: pointer;"
                         onmouseover="this.style.background='var(--color-surface)'" onmouseout="this.style.background='transparent'">
                      <template x-if="p.foto_principal_url">
                        <img :src="p.foto_principal_url" style="width: 2rem; height: 2rem; border-radius: 4px; object-fit: cover;">
                      </template>
                      <template x-if="!p.foto_principal_url">
                        <div style="width: 2rem; height: 2rem; border-radius: 4px; background: var(--color-surface); display: flex; align-items: center; justify-content: center; color: var(--color-text-muted); font-size: 0.75rem;" x-text="p.nome[0]"></div>
                      </template>
                      <div>
                        <div style="font-size: 0.875rem; color: var(--color-text);" x-text="p.nome"></div>
                        <div x-show="p.cpf_masked" style="font-size: 0.75rem; color: var(--color-text-muted);" x-text="p.cpf_masked"></div>
                      </div>
                    </div>
                  </template>
                  <!-- Cadastrar novo -->
                  <div x-show="buscaVinculo.trim().length >= 2 && !buscandoPessoa"
                       @click="iniciarCadastroNovo()"
                       style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; background: rgba(0,212,255,0.05); cursor: pointer;"
                       onmouseover="this.style.background='rgba(0,212,255,0.1)'" onmouseout="this.style.background='rgba(0,212,255,0.05)'">
                    <div style="width: 2rem; height: 2rem; border-radius: 4px; background: var(--color-primary); display: flex; align-items: center; justify-content: center; color: var(--color-bg); font-size: 0.875rem; font-weight: 700;">+</div>
                    <div>
                      <div style="font-size: 0.875rem; color: var(--color-primary); font-weight: 500;">Cadastrar novo</div>
                      <div style="font-size: 0.75rem; color: var(--color-text-muted);">Pessoa não encontrada — clique para cadastrar</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Pessoa selecionada -->
              <div x-show="pessoaSelecionada" style="display: flex; align-items: center; gap: 0.5rem; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem;">
                <div style="width: 2rem; height: 2rem; border-radius: 4px; background: var(--color-surface); display: flex; align-items: center; justify-content: center; color: var(--color-text-muted); font-size: 0.75rem;"
                     x-text="pessoaSelecionada?.nome?.[0] || ''"></div>
                <div style="flex: 1;">
                  <div style="font-size: 0.875rem; color: var(--color-text);" x-text="pessoaSelecionada?.nome"></div>
                </div>
                <button @click="pessoaSelecionada = null; buscaVinculo = ''"
                        style="color: var(--color-text-muted); font-size: 0.75rem; background: none; border: none; cursor: pointer;">trocar</button>
              </div>

              <!-- Sub-formulário: cadastrar nova pessoa -->
              <div x-show="subFormNovaPessoa" style="display: flex; flex-direction: column; gap: 0.5rem;">
                <p style="font-size: 0.75rem; color: var(--color-primary); font-weight: 500; margin: 0;">Nova pessoa</p>
                <input type="text" x-model="novaPessoaForm.nome" placeholder="Nome *"
                       style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                <input type="text" x-model="novaPessoaForm.apelido" placeholder="Apelido (opcional)"
                       style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                <input type="text" x-model="novaPessoaForm.cpf" placeholder="CPF (opcional)"
                       style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                <input type="text" x-model="novaPessoaForm.data_nascimento"
                       @input="novaPessoaForm.data_nascimento = formatarData($event.target.value)"
                       placeholder="DD/MM/AAAA" maxlength="10"
                       style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                <div style="display: flex; gap: 0.5rem;">
                  <button @click="subFormNovaPessoa = false"
                          style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                  <button @click="cadastrarNovaPessoa()"
                          :disabled="!novaPessoaForm.nome.trim()"
                          class="btn btn-primary"
                          style="flex: 1; border-radius: 4px; padding: 0.5rem; font-size: 0.875rem; font-weight: 500;">Cadastrar</button>
                </div>
              </div>

              <!-- Tipo e descrição (só aparece quando pessoa selecionada) -->
              <div x-show="pessoaSelecionada" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Tipo do vínculo <span style="color: var(--color-danger)">*</span>
                  </label>
                  <input type="text"
                         x-model="novoVinculo.tipo"
                         placeholder="Ex: Irmão, Pai, Amigo, Sócio..."
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
                  <p style="font-size: 0.75rem; color: var(--color-text-dim); margin: 0.25rem 0 0 0;">Palavra curta que define a relação</p>
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Descrição <span style="color: var(--color-text-dim)">(opcional)</span>
                  </label>
                  <textarea x-model="novoVinculo.descricao"
                            placeholder="Ex: Traficando junto na casa ao lado..."
                            rows="2"
                            style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); resize: none; box-sizing: border-box;"></textarea>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <button @click="fecharModalVinculo()"
                          style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                  <button @click="salvarVinculo()"
                          :disabled="!novoVinculo.tipo.trim()"
                          class="btn btn-primary"
                          style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">Salvar Vínculo</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Endereços -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                Endereços (<span x-text="pessoa.enderecos?.length || 0"></span>)
              </h3>
              <button @click="abrirModalNovoEndereco()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
                      onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
                + Novo Endereço
              </button>
            </div>
            <div x-show="pessoa.enderecos?.length > 0" style="display: flex; flex-direction: column; gap: 0.5rem;">
              <template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
                <div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
                  <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem; margin-bottom: 0.375rem;">
                    <span x-show="end.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
                          x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
                    <button @click="abrirModalEditarEndereco(end)"
                            style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); padding: 0.125rem; transition: color 0.15s;"
                            onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                            title="Editar endereço">
                      <svg style="width: 0.75rem; height: 0.75rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/>
                      </svg>
                    </button>
                  </div>
                  <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0;" x-text="formatEndereco(end)"></p>
                  <div style="display: flex; gap: 0.75rem; font-size: 10px; color: var(--color-text-dim); margin-top: 0.125rem;">
                    <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="idx === 0"
                          style="font-size: 10px; color: var(--color-primary); font-weight: 600; font-family: var(--font-data); background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); padding: 0 0.375rem; border-radius: 2px; letter-spacing: 0.05em; text-transform: uppercase;">
                      Atual
                    </span>
                  </div>
                </div>
              </template>
            </div>
            <p x-show="!pessoa.enderecos?.length" style="font-size: 0.75rem; color: var(--color-text-dim); text-align: center; margin: 0;">
              Nenhum endereço cadastrado
            </p>
          </div>

          <!-- Veículos Vinculados ao Abordado (container pai) -->
          <div x-show="veiculos.length > 0" class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">Veículos Vinculados ao Abordado</h3>

            <!-- Lista de veículos -->
            <div x-show="veiculos.length > 0" style="display: flex; flex-direction: column; gap: 0.5rem;">
              <template x-for="(v, idx) in veiculos" :key="v.id">
                <div class="card-led-purple" style="display: flex; align-items: center; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
                  <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; width: 100%;">
                    <div>
                      <span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.1em; background: var(--color-surface-hover); padding: 0.125rem 0.375rem; border-radius: 2px; border: 1px solid var(--color-border);" x-text="formatPlaca(v.placa)"></span>
                      <p x-show="v.modelo || v.cor || v.ano" style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"
                         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
                      <template x-if="fotosVeiculos[v.id]?.length > 0">
                        <div style="margin-top: 0.25rem;">
                          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.25rem;">
                            <template x-for="fv in fotosVeiculos[v.id].slice(0, 4)" :key="fv.id">
                              <img :src="fv.arquivo_url"
                                   style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; display: block;"
                                   @click="fotoAmpliada = fv.arquivo_url"
                                   loading="lazy">
                            </template>
                          </div>
                          <button x-show="fotosVeiculos[v.id].length > 4" @click="modalFotosVeiculo = v.id"
                                  style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.25rem 0;">
                            Ver mais (<span x-text="fotosVeiculos[v.id].length - 4"></span>)
                          </button>
                        </div>
                      </template>
                    </div>
                    <span x-show="v.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim); flex-shrink: 0;"
                          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
                </div>
              </template>
            </div>

          </div>

          <!-- Vínculos (automáticos + manuais) -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); flex: 1; margin-right: 0.5rem;">Vínculos</h3>
              <button @click="abrirModalVinculo()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
                      onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
                + Adicionar Vínculo
              </button>
            </div>

            <!-- Seção 1: Vínculos em Abordagem -->
            <div x-show="pessoa.relacionamentos?.length > 0" style="display: flex; flex-direction: column; gap: 0.25rem;">
              <p style="font-size: 10px; font-family: var(--font-data); font-weight: 600; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                Vínculos em Abordagem (<span x-text="pessoa.relacionamentos.length"></span>)
              </p>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
                  <div @click="viewPessoa(rel.pessoa_id)"
                       class="card-led-purple" style="display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; cursor: pointer;"
                       onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background='transparent'">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                      <template x-if="rel.foto_principal_url">
                        <img :src="rel.foto_principal_url"
                             style="width: 2.5rem; height: 2.5rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border); flex-shrink: 0;"
                             loading="lazy">
                      </template>
                      <template x-if="!rel.foto_principal_url">
                        <div style="width: 2.5rem; height: 2.5rem; border-radius: 4px; background: var(--color-surface-hover); border: 2px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim); flex-shrink: 0;">
                          <svg style="width: 1rem; height: 1rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                          </svg>
                        </div>
                      </template>
                      <span style="font-size: 0.875rem; color: var(--color-text-muted);" x-text="rel.nome"></span>
                    </div>
                    <div style="text-align: right;">
                      <span style="font-size: 0.75rem; color: var(--color-primary); font-weight: 500;" x-text="rel.frequencia + 'x juntos'"></span>
                      <p x-show="rel.ultima_vez" style="font-size: 10px; color: var(--color-text-dim); margin: 0;"
                         x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Separador (só quando ambas as seções têm itens) -->
            <div x-show="pessoa.relacionamentos?.length > 0 && vinculosManuais.length > 0"
                 style="border-top: 1px solid var(--color-border);"></div>

            <!-- Seção 2: Vínculos Manuais -->
            <div x-show="vinculosManuais.length > 0" style="display: flex; flex-direction: column; gap: 0.25rem;">
              <p style="font-size: 10px; font-family: var(--font-data); font-weight: 600; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                Vínculos Manuais (<span x-text="vinculosManuais.length"></span>)
              </p>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <template x-for="vm in vinculosManuais" :key="vm.id">
                  <div @click="viewPessoa(vm.pessoa_vinculada_id)"
                       class="card-led-purple" style="display: flex; align-items: flex-start; justify-content: space-between; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; cursor: pointer;"
                       onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background='transparent'">
                    <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
                      <template x-if="vm.foto_principal_url">
                        <img :src="vm.foto_principal_url"
                             style="width: 2.5rem; height: 2.5rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border); flex-shrink: 0; margin-top: 0.125rem;"
                             loading="lazy">
                      </template>
                      <template x-if="!vm.foto_principal_url">
                        <div style="width: 2.5rem; height: 2.5rem; border-radius: 4px; background: var(--color-surface-hover); border: 2px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim); flex-shrink: 0; margin-top: 0.125rem;">
                          <svg style="width: 1rem; height: 1rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                          </svg>
                        </div>
                      </template>
                      <div>
                        <span style="font-size: 0.875rem; color: var(--color-text-muted);" x-text="vm.nome"></span>
                        <p style="font-size: 0.75rem; color: #A78BFA; font-weight: 600; margin: 0.125rem 0 0 0;" x-text="vm.tipo"></p>
                        <p x-show="vm.descricao"
                           style="font-size: 0.75rem; color: var(--color-text-muted); font-style: italic; margin: 0.125rem 0 0 0;"
                           x-text="'&quot;' + vm.descricao + '&quot;'"></p>
                      </div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem; flex-shrink: 0; margin-left: 0.5rem;">
                      <span x-show="vm.criado_em" style="font-size: 10px; color: var(--color-text-dim);"
                            x-text="new Date(vm.criado_em).toLocaleDateString('pt-BR')"></span>
                      <button @click.stop="removerVinculo(vm.id)"
                              style="color: var(--color-text-dim); background: none; border: none; cursor: pointer;"
                              onmouseover="this.style.color='var(--color-danger)'" onmouseout="this.style.color='var(--color-text-dim)'"
                              title="Remover vínculo">
                        <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Mensagem quando não há vínculos -->
            <div x-show="!pessoa.relacionamentos?.length && !vinculosManuais.length"
                 style="font-size: 0.75rem; color: var(--color-text-dim); text-align: center; padding: 0.5rem 0;">
              Nenhum vínculo cadastrado
            </div>
          </div>

          <!-- Observações da Pessoa -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); flex: 1; margin-right: 0.5rem;">Observações</h3>
              <button @click="abrirModalObservacao()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
                      onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
                + Nova Observação
              </button>
            </div>

            <!-- Lista de observações -->
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <template x-for="obs in observacoes" :key="obs.id">
                <div class="card-led-purple" style="position: relative; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.25rem;">
                  <!-- Data no canto superior direito + botões de ação -->
                  <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem;">
                    <span x-show="obs.criado_em" style="font-size: 10px; color: var(--color-text-dim);"
                          x-text="new Date(obs.criado_em).toLocaleDateString('pt-BR') + ' ' + new Date(obs.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
                    <button @click="abrirModalObservacao(obs)"
                            style="color: var(--color-text-dim); background: none; border: none; cursor: pointer; padding: 0;"
                            onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                            title="Editar observação">
                      <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"/>
                      </svg>
                    </button>
                    <button @click="deletarObservacao(obs.id)"
                            style="color: var(--color-text-dim); background: none; border: none; cursor: pointer; padding: 0;"
                            onmouseover="this.style.color='var(--color-danger)'" onmouseout="this.style.color='var(--color-text-dim)'"
                            title="Remover observação">
                      <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                  <!-- Texto da observação -->
                  <p style="font-size: 0.8125rem; color: var(--color-text-muted); margin: 0; white-space: pre-wrap;" x-text="obs.texto"></p>
                </div>
              </template>
            </div>

            <!-- Mensagem quando não há observações -->
            <div x-show="!observacoes.length"
                 style="font-size: 0.75rem; color: var(--color-text-dim); text-align: center; padding: 0.5rem 0;">
              Nenhuma observação cadastrada
            </div>
          </div>

          <!-- Histórico de abordagens -->
          <div x-show="abordagens.length > 0" class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              Histórico de Abordagens (<span x-text="abordagens.length"></span>)
            </h3>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <template x-for="(ab, idx) in abordagens" :key="ab.id">
                <div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;">
                  <div style="display: flex; align-items: center; justify-content: flex-end;">
                    <span x-show="ab.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
                          x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
                  </div>
                  <div>
                    <span style="font-size: 0.75rem; font-weight: 500; color: var(--color-primary);" x-text="'#' + ab.id"></span>
                  </div>
                  <!-- Endereço da Abordagem -->
                  <div x-show="ab.endereco_texto" style="font-size: 0.75rem;">
                    <span style="color: var(--color-text-dim); font-weight: 500;">Endereço da Abordagem:</span>
                    <span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="ab.endereco_texto"></span>
                  </div>

                  <!-- Observação -->
                  <div x-show="ab.observacao" style="font-size: 0.75rem;">
                    <span style="color: var(--color-text-dim); font-weight: 500;">Observação:</span>
                    <span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="ab.observacao"></span>
                  </div>

                  <!-- Veículos desta abordagem -->
                  <template x-if="ab.veiculos?.length > 0">
                    <div style="padding-top: 0.25rem;">
                      <p style="font-size: 10px; font-family: var(--font-data); font-weight: 600; color: var(--color-text-dim); margin: 0 0 0.375rem 0; text-transform: uppercase; letter-spacing: 0.05em;">Veículos na Abordagem:</p>
                      <div style="display: flex; flex-direction: column; gap: 0.375rem;">
                        <template x-for="v in ab.veiculos" :key="v.id">
                          <div style="font-size: 0.75rem; color: var(--color-text-muted);">
                            <span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.1em; background: var(--color-surface-hover); padding: 0.125rem 0.375rem; border-radius: 2px; border: 1px solid var(--color-border);" x-text="formatPlaca(v.placa)"></span>
                            <template x-if="v.modelo || v.cor">
                              <span style="color: var(--color-text-muted);" x-text="' ' + [v.modelo, v.cor].filter(Boolean).join(' · ')"></span>
                            </template>
                            <template x-if="v.pessoa_id">
                              <span style="color: var(--color-text-dim);" x-text="' — ' + (ab.pessoas?.find(p => p.id === v.pessoa_id)?.nome || 'N/A')"></span>
                            </template>
                          </div>
                        </template>
                      </div>
                    </div>
                  </template>

                  <!-- Coabordados nesta abordagem -->
                  <template x-if="ab.pessoas?.filter(p => p.id !== ${pessoaId}).length > 0">
                    <div style="padding-top: 0.25rem;">
                      <p style="font-size: 10px; font-family: var(--font-data); font-weight: 600; color: var(--color-text-dim); margin: 0 0 0.375rem 0; text-transform: uppercase; letter-spacing: 0.05em;">Abordados juntos:</p>
                      <div style="display: flex; flex-wrap: wrap; gap: 0.75rem;">
                        <template x-for="p in ab.pessoas.filter(pp => pp.id !== ${pessoaId})" :key="p.id">
                          <div @click.stop="pessoaPreview = p"
                               style="display: flex; flex-direction: column; align-items: center; gap: 0.25rem; cursor: pointer; width: 2.5rem;">
                            <!-- Com foto -->
                            <template x-if="p.foto_principal_url">
                              <img :src="p.foto_principal_url"
                                   style="width: 2.5rem; height: 2.5rem; border-radius: 4px; object-fit: cover; border: 2px solid var(--color-border);"
                                   loading="lazy">
                            </template>
                            <!-- Sem foto: ícone silhueta -->
                            <template x-if="!p.foto_principal_url">
                              <div style="width: 2.5rem; height: 2.5rem; border-radius: 4px; background: var(--color-surface-hover); border: 2px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-dim);">
                                <svg style="width: 1.25rem; height: 1.25rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                                </svg>
                              </div>
                            </template>
                            <span style="font-size: 9px; color: var(--color-text-muted); text-align: center; line-height: 1.2; width: 2.5rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                                  x-text="p.nome.split(' ')[0]"></span>
                          </div>
                        </template>
                      </div>
                    </div>
                  </template>
                </div>
              </template>
            </div>
          </div>

          <!-- Mapa de Abordagens -->
          <div x-show="pontosComLocalizacao.length > 0" class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); flex: 1; margin-right: 0.5rem;">
                Mapa de Abordagens (<span x-text="pontosComLocalizacao.length"></span>)
              </h3>
              <div style="display: flex; gap: 0.25rem;">
                <button
                  @click="toggleModoMapa('marcadores')"
                  :aria-pressed="modoMapa === 'marcadores'"
                  style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; border: none; cursor: pointer; transition: all 0.2s;"
                  :style="modoMapa === 'marcadores' ? 'background: #14B8A6; color: var(--color-bg);' : 'background: var(--color-surface); color: var(--color-text-muted); border: 1px solid var(--color-border);'"
                >
                  Marcadores
                </button>
                <button
                  @click="toggleModoMapa('calor')"
                  :aria-pressed="modoMapa === 'calor'"
                  style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; border: none; cursor: pointer; transition: all 0.2s;"
                  :style="modoMapa === 'calor' ? 'background: #14B8A6; color: var(--color-bg);' : 'background: var(--color-surface); color: var(--color-text-muted); border: 1px solid var(--color-border);'"
                >
                  Calor
                </button>
              </div>
            </div>
            <div
              id="mapa-pessoa-${pessoaId}"
              style="width: 100%; height: 350px; border-radius: 4px; background: var(--color-surface); z-index: 1;"
            ></div>
          </div>
        </div>
      </template>

      <!-- Erro -->
      <p x-show="erro" style="color: var(--color-danger); font-size: 0.875rem;" x-text="erro"></p>
    </div>
  `;
}

function pessoaDetalhePage(pessoaId) {
  return {
    pessoa: null,
    fotos: [],
    novaFotoFile: null,
    novaFotoPreviewUrl: "",
    uploadandoFoto: false,
    fotosVeiculos: {},
    abordagens: [],
    veiculos: [],
    fotoAmpliada: null,
    modalTodasFotos: false,
    modalFotosVeiculo: null,
    pessoaPreview: null,
    loading: true,
    erro: null,
    mapaInst: null,
    clusterLayer: null,
    heatLayer: null,
    modoMapa: 'marcadores',
    pontosComLocalizacao: [],
    _mapaObserver: null,

    // Vínculos manuais
    vinculosManuais: [],
    modalVinculo: false,
    buscaVinculo: '',
    resultadosBusca: [],
    buscandoPessoa: false,
    pessoaSelecionada: null,
    novoVinculo: { tipo: '', descricao: '' },
    subFormNovaPessoa: false,
    novaPessoaForm: { nome: '', cpf: '', apelido: '', data_nascimento: '' },
    _buscaTimer: null,

    // Observações
    observacoes: [],
    modalObservacao: false,
    obsForm: { id: null, texto: '' },
    salvandoObs: false,

    /**
     * Calcula a idade em anos completos a partir da data de nascimento.
     *
     * @param {string|null} dataNascimento - Data no formato ISO 'YYYY-MM-DD'.
     * @returns {number|null} Idade em anos, ou null se a data for inválida ou ausente.
     */
    calcularIdade(dataNascimento) {
      if (!dataNascimento) return null;
      const nasc = new Date(dataNascimento + 'T00:00:00');
      if (isNaN(nasc.getTime())) return null;
      const hoje = new Date();
      let idade = hoje.getFullYear() - nasc.getFullYear();
      const m = hoje.getMonth() - nasc.getMonth();
      if (m < 0 || (m === 0 && hoje.getDate() < nasc.getDate())) idade--;
      return idade;
    },

    /**
     * Formata a data de nascimento com a idade calculada.
     *
     * @param {string|null} dataNascimento - Data no formato ISO 'YYYY-MM-DD'.
     * @param {string} fallback - Valor retornado quando data é ausente (padrão: '—').
     * @returns {string} Data formatada com idade, ex: "24/10/2007 (18 anos)", ou o fallback.
     */
    formatarNascimento(dataNascimento, fallback = '—') {
      if (!dataNascimento) return fallback;
      const data = new Date(dataNascimento + 'T00:00:00');
      if (isNaN(data.getTime())) return fallback;
      const dataFormatada = data.toLocaleDateString('pt-BR');
      const idade = this.calcularIdade(dataNascimento);
      return idade !== null ? `${dataFormatada} (${idade} anos)` : dataFormatada;
    },

    // Edição de dados pessoais
    modalEditarPessoa: false,
    editPessoaForm: { nome: '', cpf: '', data_nascimento: '', apelido: '', observacoes: '' },
    salvandoPessoa: false,

    // Edição de endereço
    modalEditarEndereco: false,
    editEnderecoForm: { id: null, endereco: '' },
    enderecoEstadoId: null,
    enderecoEstadoNome: '',
    enderecoCidadeId: null,
    enderecoCidadeTexto: '',
    enderecoBairroId: null,
    enderecoBairroTexto: '',
    enderecoEstados: [],
    enderecoCidadeSugestoes: [],
    enderecoBairroSugestoes: [],
    enderecoCidadeCadastrarNovo: false,
    enderecoBairroCadastrarNovo: false,
    salvandoEndereco: false,
    modoEndereco: 'criar',

    async load() {
      try {
        // Buscar pessoa com detalhes
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.vinculosManuais = this.pessoa.vinculos_manuais || [];
        // Carregar observações da pessoa
        await this.carregarObservacoes();

        // Buscar fotos da pessoa
        try {
          this.fotos = await api.get(`/fotos/pessoa/${pessoaId}`);
        } catch {
          this.fotos = [];
        }

        // Buscar abordagens da pessoa (usando consulta geral)
        await this.carregarAbordagens();
      } catch (err) {
        this.erro = err.message || "Erro ao carregar pessoa.";
      } finally {
        this.loading = false;
      }
      // Após loading=false o x-if renderiza o conteúdo — agora o div do mapa existe
      await this.setupMapaObserver();
    },

    async carregarAbordagens() {
      // Limpar observer anterior se existir
      if (this._mapaObserver) {
        this._mapaObserver.disconnect();
        this._mapaObserver = null;
      }

      try {
        const abordagens = await api.get(`/pessoas/${pessoaId}/abordagens`);
        this.abordagens = abordagens;

        // Carregar fotos de veículo/placa de todas as abordagens em paralelo
        const fotosPromises = abordagens.map(ab =>
          api.get(`/fotos/abordagem/${ab.id}`).catch(() => [])
        );
        const fotosResultados = await Promise.all(fotosPromises);
        const tiposVeiculo = ['veiculo', 'placa'];
        const fotosPlanas = fotosResultados.flat().filter(f => tiposVeiculo.includes(f.tipo));
        // Mapa veiculo_id → array de todas as fotos do veículo
        const mapaFotos = {};
        for (const foto of fotosPlanas) {
          if (foto.veiculo_id) {
            if (!mapaFotos[foto.veiculo_id]) mapaFotos[foto.veiculo_id] = [];
            mapaFotos[foto.veiculo_id].push(foto);
          }
        }
        this.fotosVeiculos = mapaFotos;

        // Coletar veículos únicos da pessoa (veículos vinculados ao abordado)
        const veiculosMap = {};
        for (const ab of abordagens) {
          for (const v of ab.veiculos || []) {
            if (v.pessoa_id === pessoaId || v.pessoa_id === null) {
              veiculosMap[v.id] = v;
            }
          }
        }
        this.veiculos = Object.values(veiculosMap);

        // Extrair pontos com coordenadas para o mapa
        this.pontosComLocalizacao = abordagens
          .filter(ab => typeof ab.latitude === 'number' && isFinite(ab.latitude)
                     && typeof ab.longitude === 'number' && isFinite(ab.longitude))
          .map(ab => ({
            lat: ab.latitude,
            lng: ab.longitude,
            dataHora: ab.data_hora
              ? new Date(ab.data_hora).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
              : (ab.criado_em ? new Date(ab.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'),
            endereco: ab.endereco_texto || '',
          }));

      } catch { /* silencioso */ }
    },

    async setupMapaObserver() {
      if (this.pontosComLocalizacao.length === 0) return;
      if (this._mapaObserver) {
        this._mapaObserver.disconnect();
        this._mapaObserver = null;
      }
      // x-if usa múltiplos níveis de microtask para renderizar o template.
      // $nextTick() (microtask) pode resolver antes que o DOM esteja pronto.
      // setTimeout(0) garante que todos os microtasks pendentes do Alpine
      // completem antes de buscar o div.
      await new Promise(r => setTimeout(r, 0));
      const divId = `mapa-pessoa-${pessoaId}`;
      const div = document.getElementById(divId);
      if (!div) return;
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          this.initMapa();
        }
      }, { threshold: 0.1 });
      observer.observe(div);
      this._mapaObserver = observer;
    },

    initMapa() {
      const divId = `mapa-pessoa-${pessoaId}`;
      const div = document.getElementById(divId);
      if (!div || this.mapaInst) return;
      if (typeof L === 'undefined') return;

      this.mapaInst = L.map(div, { zoomControl: true });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(this.mapaInst);

      const pontos = this.pontosComLocalizacao;

      // Camada de marcadores agrupados
      this.clusterLayer = L.markerClusterGroup();
      for (const p of pontos) {
        const marker = L.marker([p.lat, p.lng]);
        marker.bindPopup(`<b>${p.dataHora}</b><br>${p.endereco || 'Endereço não informado'}`);
        this.clusterLayer.addLayer(marker);
      }

      // Camada de calor
      const heatPontos = pontos.map(p => [p.lat, p.lng, 1]);
      this.heatLayer = L.heatLayer(heatPontos, {
        radius: 30,
        blur: 20,
        maxZoom: 17,
        gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' },
      });

      // Modo inicial: marcadores
      this.mapaInst.addLayer(this.clusterLayer);

      // Ajusta zoom para cobrir todos os pontos
      if (pontos.length === 1) {
        this.mapaInst.setView([pontos[0].lat, pontos[0].lng], 15);
      } else {
        const bounds = L.latLngBounds(pontos.map(p => [p.lat, p.lng]));
        this.mapaInst.fitBounds(bounds, { padding: [30, 30] });
      }

      // Força recálculo das dimensões após o container estar completamente visível.
      // O IntersectionObserver dispara em threshold=0.1, mas o container pode ainda
      // não ter dimensões estáveis — múltiplas chamadas garantem que pelo menos uma
      // acerta o momento em que o flex layout já foi calculado pelo browser.
      requestAnimationFrame(() => {
        this.mapaInst && this.mapaInst.invalidateSize({ animate: false });
        setTimeout(() => this.mapaInst && this.mapaInst.invalidateSize({ animate: false }), 200);
        setTimeout(() => this.mapaInst && this.mapaInst.invalidateSize({ animate: false }), 500);
      });
    },

    toggleModoMapa(modo) {
      if (!this.mapaInst || modo === this.modoMapa) return;
      this.modoMapa = modo;
      if (modo === 'marcadores') {
        this.mapaInst.removeLayer(this.heatLayer);
        this.mapaInst.addLayer(this.clusterLayer);
      } else {
        this.mapaInst.removeLayer(this.clusterLayer);
        this.mapaInst.addLayer(this.heatLayer);
      }
    },

    formatEndereco(end) {
      if (!end) return "";
      const parts = [end.endereco, end.bairro, end.cidade, end.estado].filter(Boolean);
      return parts.join(", ");
    },

    formatPlaca(placa) {
      if (!placa) return '—';
      const p = placa.toUpperCase().replace(/-/g, '');
      if (p.length >= 4) return p.slice(0, 3) + '-' + p.slice(3);
      return p;
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },

    goBack() {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) appEl._x_dataStack[0].goBack();
    },

    // ------- Vínculos Manuais -------

    abrirModalVinculo() {
      this.modalVinculo = true;
      this.buscaVinculo = '';
      this.resultadosBusca = [];
      this.pessoaSelecionada = null;
      this.novoVinculo = { tipo: '', descricao: '' };
      this.subFormNovaPessoa = false;
      this.novaPessoaForm = { nome: '', cpf: '', apelido: '', data_nascimento: '' };
    },

    fecharModalVinculo() {
      this.modalVinculo = false;
    },

    onBuscaVinculo() {
      clearTimeout(this._buscaTimer);
      const q = this.buscaVinculo.trim();
      if (q.length < 2) { this.resultadosBusca = []; return; }
      this._buscaTimer = setTimeout(() => this._executarBusca(q), 400);
    },

    async _executarBusca(q) {
      this.buscandoPessoa = true;
      try {
        const results = await api.get(`/pessoas/?nome=${encodeURIComponent(q)}&limit=5`);
        // Excluir a própria pessoa da lista
        // pessoaId é closure da função pessoaDetalhePage(pessoaId) — NÃO usar ${} aqui
        this.resultadosBusca = results.filter(p => p.id !== pessoaId);
      } catch { this.resultadosBusca = []; }
      finally { this.buscandoPessoa = false; }
    },

    selecionarPessoa(p) {
      this.pessoaSelecionada = p;
      this.resultadosBusca = [];
      this.subFormNovaPessoa = false;
    },

    iniciarCadastroNovo() {
      this.pessoaSelecionada = null;
      this.subFormNovaPessoa = true;
      this.novaPessoaForm.nome = this.buscaVinculo.trim();
    },

    async cadastrarNovaPessoa() {
      if (!this.novaPessoaForm.nome.trim()) return;
      try {
        const nova = await api.post('/pessoas/', {
          nome: this.novaPessoaForm.nome,
          cpf: this.novaPessoaForm.cpf || undefined,
          apelido: this.novaPessoaForm.apelido || undefined,
          data_nascimento: parseDateBR(this.novaPessoaForm.data_nascimento) || undefined,
        });
        this.selecionarPessoa(nova);
      } catch (err) {
        alert(err.message || 'Erro ao cadastrar pessoa.');
      }
    },

    async salvarVinculo() {
      if (!this.pessoaSelecionada || !this.novoVinculo.tipo.trim()) return;
      try {
        const vinculo = await api.post(`/pessoas/${pessoaId}/vinculos-manuais`, {
          pessoa_vinculada_id: this.pessoaSelecionada.id,
          tipo: this.novoVinculo.tipo.trim(),
          descricao: this.novoVinculo.descricao.trim() || undefined,
        });
        this.vinculosManuais.unshift(vinculo);
        this.fecharModalVinculo();
      } catch (err) {
        alert(err.message || 'Erro ao salvar vínculo.');
      }
    },

    async removerVinculo(vinculoId) {
      if (!confirm('Remover este vínculo?')) return;
      try {
        await api.del(`/pessoas/${pessoaId}/vinculos-manuais/${vinculoId}`);
        this.vinculosManuais = this.vinculosManuais.filter(v => v.id !== vinculoId);
      } catch (err) {
        alert(err.message || 'Erro ao remover vínculo.');
      }
    },

    async carregarObservacoes() {
      try {
        this.observacoes = await api.get(`/pessoas/${pessoaId}/observacoes`);
      } catch {
        this.observacoes = [];
      }
    },

    abrirModalObservacao(obs = null) {
      if (obs) {
        this.obsForm = { id: obs.id, texto: obs.texto };
      } else {
        this.obsForm = { id: null, texto: '' };
      }
      this.modalObservacao = true;
    },

    async salvarObservacao() {
      if (!this.obsForm.texto.trim()) return;
      this.salvandoObs = true;
      try {
        if (this.obsForm.id) {
          const atualizada = await api.patch(
            `/pessoas/${pessoaId}/observacoes/${this.obsForm.id}`,
            { texto: this.obsForm.texto.trim() }
          );
          const idx = this.observacoes.findIndex(o => o.id === this.obsForm.id);
          if (idx !== -1) this.observacoes[idx] = atualizada;
        } else {
          const nova = await api.post(`/pessoas/${pessoaId}/observacoes`, {
            texto: this.obsForm.texto.trim()
          });
          this.observacoes.unshift(nova);
        }
        this.modalObservacao = false;
        this.obsForm = { id: null, texto: '' };
      } catch (err) {
        alert(err.message || 'Erro ao salvar observação.');
      } finally {
        this.salvandoObs = false;
      }
    },

    async deletarObservacao(obsId) {
      if (!confirm('Remover esta observação?')) return;
      try {
        await api.del(`/pessoas/${pessoaId}/observacoes/${obsId}`);
        this.observacoes = this.observacoes.filter(o => o.id !== obsId);
      } catch (err) {
        alert(err.message || 'Erro ao remover observação.');
      }
    },

    // ------- Edição de Dados Pessoais -------

    abrirModalEditarPessoa() {
      const p = this.pessoa;
      this.editPessoaForm = {
        nome: p.nome || '',
        cpf: p.cpf || '',
        data_nascimento: p.data_nascimento
          ? new Date(p.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR')
          : '',
        apelido: p.apelido || '',
        observacoes: p.observacoes || '',
      };
      this.modalEditarPessoa = true;
    },

    async salvarEditPessoa() {
      if (!this.editPessoaForm.nome.trim()) return;
      this.salvandoPessoa = true;
      try {
        const body = {};
        const f = this.editPessoaForm;
        if (f.nome.trim() !== (this.pessoa.nome || '')) body.nome = f.nome.trim();
        if (f.cpf.trim() !== (this.pessoa.cpf || '')) body.cpf = f.cpf.trim() || null;
        if (f.apelido.trim() !== (this.pessoa.apelido || '')) body.apelido = f.apelido.trim() || null;
        if (f.observacoes.trim() !== (this.pessoa.observacoes || '')) body.observacoes = f.observacoes.trim() || null;

        const dataParsed = parseDateBR(f.data_nascimento);
        const dataAtual = this.pessoa.data_nascimento || null;
        if (dataParsed !== dataAtual) body.data_nascimento = dataParsed || null;

        if (Object.keys(body).length === 0) {
          this.modalEditarPessoa = false;
          return;
        }

        await api.patch(`/pessoas/${pessoaId}`, body);

        // Recarregar dados atualizados
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.vinculosManuais = this.pessoa.vinculos_manuais || [];
        this.modalEditarPessoa = false;
        showToast('Dados atualizados com sucesso!', 'success');
      } catch (err) {
        showToast(err?.message || 'Erro ao atualizar dados.', 'error');
      } finally {
        this.salvandoPessoa = false;
      }
    },

    // ------- Edição/Criação de Endereço -------

    async carregarEstados() {
      if (this.enderecoEstados.length > 0) return;
      try {
        this.enderecoEstados = await api.get('/localidades?tipo=estado');
      } catch (e) {
        console.error('Erro ao carregar estados', e);
      }
    },

    async buscarCidades() {
      const q = this.enderecoCidadeTexto.trim();
      if (!this.enderecoEstadoId || q.length < 2) {
        this.enderecoCidadeSugestoes = [];
        this.enderecoCidadeCadastrarNovo = false;
        return;
      }
      try {
        const resultado = await api.get(
          `/localidades?tipo=cidade&parent_id=${this.enderecoEstadoId}&q=${encodeURIComponent(q)}`
        );
        this.enderecoCidadeSugestoes = resultado;
        this.enderecoCidadeCadastrarNovo = resultado.length === 0;
      } catch (e) {
        console.error('Erro ao buscar cidades', e);
      }
    },

    async buscarBairros() {
      const q = this.enderecoBairroTexto.trim();
      if (!this.enderecoCidadeId || q.length < 2) {
        this.enderecoBairroSugestoes = [];
        this.enderecoBairroCadastrarNovo = false;
        return;
      }
      try {
        const resultado = await api.get(
          `/localidades?tipo=bairro&parent_id=${this.enderecoCidadeId}&q=${encodeURIComponent(q)}`
        );
        this.enderecoBairroSugestoes = resultado;
        this.enderecoBairroCadastrarNovo = resultado.length === 0;
      } catch (e) {
        console.error('Erro ao buscar bairros', e);
      }
    },

    selecionarCidade(cidade) {
      this.enderecoCidadeId = cidade.id;
      this.enderecoCidadeTexto = cidade.nome_exibicao;
      this.enderecoCidadeSugestoes = [];
      this.enderecoCidadeCadastrarNovo = false;
      this.enderecoBairroId = null;
      this.enderecoBairroTexto = '';
    },

    selecionarBairro(bairro) {
      this.enderecoBairroId = bairro.id;
      this.enderecoBairroTexto = bairro.nome_exibicao;
      this.enderecoBairroSugestoes = [];
      this.enderecoBairroCadastrarNovo = false;
    },

    async cadastrarNovaCidade() {
      const nome = this.enderecoCidadeTexto.trim();
      if (!nome || !this.enderecoEstadoId) return;
      try {
        const nova = await api.post('/localidades', {
          nome,
          tipo: 'cidade',
          parent_id: parseInt(this.enderecoEstadoId),
        });
        this.selecionarCidade(nova);
      } catch (e) {
        showToast('Erro ao cadastrar cidade', 'error');
      }
    },

    async cadastrarNovoBairro() {
      const nome = this.enderecoBairroTexto.trim();
      if (!nome || !this.enderecoCidadeId) return;
      try {
        const novo = await api.post('/localidades', {
          nome,
          tipo: 'bairro',
          parent_id: this.enderecoCidadeId,
        });
        this.selecionarBairro(novo);
      } catch (e) {
        showToast('Erro ao cadastrar bairro', 'error');
      }
    },

    abrirModalEditarEndereco(end) {
      this.modoEndereco = 'editar';
      this.editEnderecoForm = { id: end.id, endereco: end.endereco || '' };
      this.enderecoEstadoId = end.estado_id || null;
      this.enderecoCidadeId = end.cidade_id || null;
      this.enderecoCidadeTexto = end.cidade || '';
      this.enderecoBairroId = end.bairro_id || null;
      this.enderecoBairroTexto = end.bairro || '';
      this.carregarEstados();
      this.modalEditarEndereco = true;
    },

    abrirModalNovoEndereco() {
      this.modoEndereco = 'criar';
      this.editEnderecoForm = { id: null, endereco: '' };
      this.enderecoEstadoId = null;
      this.enderecoCidadeId = null;
      this.enderecoCidadeTexto = '';
      this.enderecoBairroId = null;
      this.enderecoBairroTexto = '';
      this.carregarEstados();
      this.modalEditarEndereco = true;
    },

    async salvarEditEndereco() {
      if (!this.editEnderecoForm.endereco.trim()) return;
      this.salvandoEndereco = true;
      try {
        const f = this.editEnderecoForm;
        const body = {
          endereco: f.endereco.trim(),
          estado_id: this.enderecoEstadoId ? parseInt(this.enderecoEstadoId) : null,
          cidade_id: this.enderecoCidadeId || null,
          bairro_id: this.enderecoBairroId || null,
        };

        if (this.modoEndereco === 'editar') {
          await api.patch(`/pessoas/${pessoaId}/enderecos/${f.id}`, body);
        } else {
          await api.post(`/pessoas/${pessoaId}/enderecos`, body);
        }

        // Recarregar dados atualizados
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.vinculosManuais = this.pessoa.vinculos_manuais || [];
        this.modalEditarEndereco = false;
        showToast(
          this.modoEndereco === 'editar' ? 'Endereço atualizado!' : 'Endereço cadastrado!',
          'success'
        );
      } catch (err) {
        showToast(err?.message || 'Erro ao salvar endereço.', 'error');
      } finally {
        this.salvandoEndereco = false;
      }
    },

    onNovaFotoSelected(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
      this.novaFotoFile = file;
      this.novaFotoPreviewUrl = URL.createObjectURL(file);
      event.target.value = "";
    },

    cancelarNovaFoto() {
      if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
      this.novaFotoFile = null;
      this.novaFotoPreviewUrl = "";
    },

    async uploadNovaFoto() {
      if (!this.novaFotoFile) return;
      this.uploadandoFoto = true;
      try {
        await api.uploadFile("/fotos/upload", this.novaFotoFile, {
          tipo: "rosto",
          pessoa_id: parseInt(pessoaId, 10),
        });
        // Recarregar lista de fotos
        this.fotos = await api.get(`/fotos/pessoa/${pessoaId}`);
        // Limpar estado
        this.cancelarNovaFoto();
        showToast("Foto adicionada com sucesso!", "success");
      } catch (err) {
        showToast(err?.message || "Erro ao enviar foto", "error");
      } finally {
        this.uploadandoFoto = false;
      }
    },
  };
}
