/**
 * Página de detalhe de pessoa — Argus AI.
 *
 * Exibe dados pessoais, fotos, endereços, relacionamentos
 * (vínculos com outras pessoas), veículos e histórico de abordagens.
 * Todas as informações aparecem sem ocultação.
 */
const PALETTE = [
  'border-l-blue-500',
  'border-l-green-500',
  'border-l-orange-500',
  'border-l-purple-500',
  'border-l-teal-500',
  'border-l-yellow-500',
  'border-l-red-400',
  'border-l-pink-500',
];

function renderPessoaDetalhe(appState) {
  const pessoaId = appState._pessoaId;
  if (!pessoaId) {
    return `<p class="text-slate-400">Nenhuma pessoa selecionada.</p>`;
  }

  return `
    <div x-data="pessoaDetalhePage(${pessoaId})" x-init="load()" class="space-y-4 pb-24">
      <!-- Loading -->
      <div x-show="loading" class="flex justify-center py-12">
        <span class="spinner"></span>
      </div>

      <!-- Conteúdo -->
      <template x-if="pessoa && !loading">
        <div class="space-y-4">
          <!-- Header -->
          <div>
            <button @click="goBack()" class="text-blue-400 text-sm mb-2">&larr; Voltar</button>
            <h2 class="text-xl font-bold text-slate-100" x-text="pessoa.nome"></h2>
            <p x-show="pessoa.apelido" class="text-sm text-yellow-400 font-medium" x-text="'Vulgo: ' + pessoa.apelido"></p>
          </div>

          <!-- Dados pessoais -->
          <div class="card space-y-2 border-l-4 border-l-slate-400">
            <h3 class="text-sm font-semibold text-slate-300">Dados Pessoais</h3>
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span class="text-slate-500">CPF:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.cpf || pessoa.cpf_masked || '—'"></span>
              </div>
              <div>
                <span class="text-slate-500">Cadastro:</span>
                <span class="text-slate-300 ml-1" x-text="new Date(pessoa.criado_em).toLocaleDateString('pt-BR')"></span>
              </div>
              <div>
                <span class="text-slate-500">Nascimento:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.data_nascimento ? new Date(pessoa.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '—'"></span>
              </div>
              <div>
                <span class="text-slate-500">Abordagens:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.abordagens_count || 0"></span>
              </div>
            </div>
            <div x-show="pessoa.observacoes" class="pt-1">
              <span class="text-xs text-slate-500">Obs:</span>
              <p class="text-xs text-slate-400" x-text="pessoa.observacoes"></p>
            </div>
          </div>

          <!-- Fotos -->
          <div class="card space-y-2 border-l-4 border-l-amber-500">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-300">
                Fotos (<span x-text="fotos.length"></span>)
              </h3>
              <!-- Botões câmera + galeria -->
              <div class="flex gap-1.5">
                <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400 hover:bg-slate-600 transition-colors">
                  📷
                  <input type="file" accept="image/*" capture="environment" class="hidden"
                         @change="onNovaFotoSelected($event)">
                </label>
                <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400 hover:bg-slate-600 transition-colors">
                  📁
                  <input type="file" accept="image/*" class="hidden"
                         @change="onNovaFotoSelected($event)">
                </label>
              </div>
            </div>

            <!-- Preview + botão enviar (aparece após selecionar) -->
            <template x-if="novaFotoFile">
              <div class="flex items-center gap-3 p-2 bg-slate-700/50 rounded-lg">
                <img :src="novaFotoPreviewUrl" class="w-12 h-12 rounded object-cover shrink-0">
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-slate-400 truncate" x-text="novaFotoFile?.name"></p>
                </div>
                <div class="flex gap-1.5 shrink-0">
                  <button @click="uploadNovaFoto()"
                          :disabled="uploadandoFoto"
                          class="text-xs px-2 py-1 rounded bg-green-700 text-green-200 hover:bg-green-600 transition-colors disabled:opacity-50">
                    <span x-show="!uploadandoFoto">Enviar</span>
                    <span x-show="uploadandoFoto" class="spinner"></span>
                  </button>
                  <button @click="if (novaFotoPreviewUrl) URL.revokeObjectURL(novaFotoPreviewUrl); novaFotoFile = null; novaFotoPreviewUrl = ''"
                          class="text-xs px-2 py-1 rounded bg-slate-600 text-slate-400 hover:bg-slate-500 transition-colors">
                    ✕
                  </button>
                </div>
              </div>
            </template>

            <!-- Grid de fotos existentes -->
            <div x-show="fotos.length > 0" class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <div>
                  <div class="relative">
                    <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                         @click="fotoAmpliada = foto.arquivo_url">
                    <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                          x-text="foto.tipo || 'foto'"></span>
                  </div>
                  <p class="text-xs text-slate-400 text-center mt-1"
                     x-show="foto.data_hora"
                     x-text="foto.data_hora ? new Date(foto.data_hora).toLocaleDateString('pt-BR') : ''"></p>
                </div>
              </template>
            </div>

            <!-- Estado vazio -->
            <p x-show="fotos.length === 0 && !novaFotoFile" class="text-xs text-slate-500">
              Nenhuma foto cadastrada.
            </p>
          </div>

          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
            <img :src="fotoAmpliada" class="max-w-full max-h-full rounded-lg">
          </div>

          <!-- Modal preview de pessoa coabordada -->
          <div x-show="pessoaPreview" x-cloak
               @click.self="pessoaPreview = null"
               class="fixed inset-0 bg-black/60 z-50 flex items-end justify-center sm:items-center p-4">
            <div @click="viewPessoa(pessoaPreview.id)"
                 class="bg-slate-800 border border-slate-600 rounded-2xl p-5 w-full max-w-sm space-y-3 cursor-pointer hover:border-blue-500 transition-colors">
              <!-- Foto ou ícone -->
              <div class="flex justify-center">
                <template x-if="pessoaPreview?.foto_principal_url">
                  <img :src="pessoaPreview.foto_principal_url"
                       class="w-20 h-20 rounded-full object-cover border-2 border-slate-500">
                </template>
                <template x-if="!pessoaPreview?.foto_principal_url">
                  <div class="w-20 h-20 rounded-full bg-slate-700 border-2 border-slate-500 flex items-center justify-center text-slate-400">
                    <svg class="w-10 h-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                    </svg>
                  </div>
                </template>
              </div>
              <!-- Dados -->
              <div class="text-center space-y-1">
                <p class="text-base font-bold text-slate-100" x-text="pessoaPreview?.nome"></p>
                <p x-show="pessoaPreview?.apelido"
                   class="text-sm text-yellow-400 font-medium"
                   x-text="'Vulgo: ' + pessoaPreview?.apelido"></p>
                <p x-show="pessoaPreview?.cpf_masked"
                   class="text-xs text-slate-400"
                   x-text="'CPF: ' + pessoaPreview?.cpf_masked"></p>
                <p x-show="pessoaPreview?.data_nascimento"
                   class="text-xs text-slate-400"
                   x-text="'Nascimento: ' + (pessoaPreview?.data_nascimento ? new Date(pessoaPreview.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '')"></p>
              </div>
              <!-- Botão -->
              <div class="pt-1">
                <div class="w-full text-center text-sm font-semibold text-blue-400 py-2 rounded-lg border border-blue-500/40 bg-blue-500/10">
                  Ver ficha completa →
                </div>
              </div>
            </div>
          </div>

          <!-- Modal de cadastro de vínculo manual -->
          <div x-show="modalVinculo" x-cloak
               @click.self="fecharModalVinculo()"
               class="fixed inset-0 bg-black/60 z-50 flex items-end justify-center sm:items-center p-4">
            <div class="bg-slate-800 border border-slate-600 rounded-2xl p-5 w-full max-w-sm space-y-4"
                 @click.stop>
              <div class="flex items-center justify-between">
                <h3 class="text-base font-semibold text-slate-100">Cadastrar Vínculo Manual</h3>
                <button @click="fecharModalVinculo()" class="text-slate-400 hover:text-slate-200 text-lg leading-none">&times;</button>
              </div>

              <!-- Busca de pessoa -->
              <div x-show="!pessoaSelecionada && !subFormNovaPessoa">
                <label class="text-xs text-slate-400 font-medium block mb-1">Buscar pessoa</label>
                <input type="text"
                       x-model="buscaVinculo"
                       @input="onBuscaVinculo()"
                       placeholder="Nome, apelido ou CPF..."
                       class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">

                <!-- Loading -->
                <div x-show="buscandoPessoa" class="flex justify-center py-2">
                  <span class="spinner"></span>
                </div>

                <!-- Resultados -->
                <div x-show="resultadosBusca.length > 0 || (buscaVinculo.trim().length >= 2 && !buscandoPessoa)"
                     class="mt-1 bg-slate-700 border border-slate-600 rounded-lg overflow-hidden">
                  <template x-for="p in resultadosBusca" :key="p.id">
                    <div @click="selecionarPessoa(p)"
                         class="flex items-center gap-2 px-3 py-2 border-b border-slate-600 last:border-0 cursor-pointer hover:bg-slate-600 transition-colors">
                      <template x-if="p.foto_principal_url">
                        <img :src="p.foto_principal_url" class="w-7 h-7 rounded-full object-cover">
                      </template>
                      <template x-if="!p.foto_principal_url">
                        <div class="w-7 h-7 rounded-full bg-slate-500 flex items-center justify-center text-slate-300 text-xs" x-text="p.nome[0]"></div>
                      </template>
                      <div>
                        <div class="text-sm text-slate-100" x-text="p.nome"></div>
                        <div x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="p.cpf_masked"></div>
                      </div>
                    </div>
                  </template>
                  <!-- Cadastrar novo -->
                  <div x-show="buscaVinculo.trim().length >= 2 && !buscandoPessoa"
                       @click="iniciarCadastroNovo()"
                       class="flex items-center gap-2 px-3 py-2 bg-blue-900/30 cursor-pointer hover:bg-blue-900/50 transition-colors">
                    <div class="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">+</div>
                    <div>
                      <div class="text-sm text-blue-400 font-medium">Cadastrar novo</div>
                      <div class="text-xs text-slate-400">Pessoa não encontrada — clique para cadastrar</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Pessoa selecionada -->
              <div x-show="pessoaSelecionada" class="flex items-center gap-2 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2">
                <div class="w-7 h-7 rounded-full bg-slate-500 flex items-center justify-center text-slate-300 text-xs"
                     x-text="pessoaSelecionada?.nome?.[0] || ''"></div>
                <div class="flex-1">
                  <div class="text-sm text-slate-100" x-text="pessoaSelecionada?.nome"></div>
                </div>
                <button @click="pessoaSelecionada = null; buscaVinculo = ''"
                        class="text-slate-400 hover:text-slate-200 text-xs">trocar</button>
              </div>

              <!-- Sub-formulário: cadastrar nova pessoa -->
              <div x-show="subFormNovaPessoa" class="space-y-2">
                <p class="text-xs text-blue-400 font-medium">Nova pessoa</p>
                <input type="text" x-model="novaPessoaForm.nome" placeholder="Nome *"
                       class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
                <input type="text" x-model="novaPessoaForm.apelido" placeholder="Apelido (opcional)"
                       class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
                <input type="text" x-model="novaPessoaForm.cpf" placeholder="CPF (opcional)"
                       class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
                <input type="date" x-model="novaPessoaForm.data_nascimento"
                       class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500">
                <div class="flex gap-2">
                  <button @click="subFormNovaPessoa = false"
                          class="flex-1 bg-slate-600 text-slate-300 rounded-lg py-2 text-sm">Cancelar</button>
                  <button @click="cadastrarNovaPessoa()"
                          :disabled="!novaPessoaForm.nome.trim()"
                          class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg py-2 text-sm font-medium transition-colors">Cadastrar</button>
                </div>
              </div>

              <!-- Tipo e descrição (só aparece quando pessoa selecionada) -->
              <div x-show="pessoaSelecionada" class="space-y-3">
                <div>
                  <label class="text-xs text-slate-400 font-medium block mb-1">
                    Tipo do vínculo <span class="text-red-400">*</span>
                  </label>
                  <input type="text"
                         x-model="novoVinculo.tipo"
                         placeholder="Ex: Irmão, Pai, Amigo, Sócio..."
                         class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
                  <p class="text-xs text-slate-500 mt-1">Palavra curta que define a relação</p>
                </div>
                <div>
                  <label class="text-xs text-slate-400 font-medium block mb-1">
                    Descrição <span class="text-slate-500">(opcional)</span>
                  </label>
                  <textarea x-model="novoVinculo.descricao"
                            placeholder="Ex: Traficando junto na casa ao lado..."
                            rows="2"
                            class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"></textarea>
                </div>
                <div class="flex gap-2">
                  <button @click="fecharModalVinculo()"
                          class="flex-1 bg-slate-600 text-slate-300 rounded-lg py-2.5 text-sm">Cancelar</button>
                  <button @click="salvarVinculo()"
                          :disabled="!novoVinculo.tipo.trim()"
                          class="flex-2 flex-grow bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg py-2.5 text-sm font-medium transition-colors">Salvar Vínculo</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Endereços -->
          <div x-show="pessoa.enderecos?.length > 0" class="card space-y-2 border-l-4 border-l-blue-600">
            <h3 class="text-sm font-semibold text-slate-300">
              Endereços (<span x-text="pessoa.enderecos.length"></span>)
            </h3>
            <div class="space-y-2">
              <template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
                <div class="border border-slate-700/40 border-l-4 rounded-lg p-3" :class="PALETTE[idx % PALETTE.length]">
                  <div class="flex items-start justify-between gap-2">
                    <p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
                    <span x-show="end.criado_em" class="text-xs text-slate-500 shrink-0"
                          x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
                  <div class="flex gap-3 text-[10px] text-slate-500 mt-0.5">
                    <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Veículos Vinculados ao Abordado (container pai) -->
          <div x-show="veiculos.length > 0" class="card space-y-3 border-l-4 border-l-emerald-500">
            <h3 class="text-sm font-semibold text-slate-300">Veículos Vinculados ao Abordado</h3>

            <!-- Lista de veículos -->
            <div x-show="veiculos.length > 0" class="space-y-2">
              <template x-for="(v, idx) in veiculos" :key="v.id">
                <div class="flex items-center border border-slate-700/40 border-l-4 rounded-lg p-3" :class="PALETTE[idx % PALETTE.length]">
                  <div class="flex items-start justify-between gap-2 w-full">
                    <div>
                      <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
                      <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
                         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
                      <template x-if="fotosVeiculos[v.id]">
                        <img :src="fotosVeiculos[v.id].arquivo_url"
                             class="w-16 h-16 object-cover rounded-lg cursor-pointer mt-1"
                             @click="fotoAmpliada = fotosVeiculos[v.id].arquivo_url"
                             loading="lazy">
                      </template>
                    </div>
                    <span x-show="v.criado_em" class="text-xs text-slate-500 shrink-0"
                          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
                </div>
              </template>
            </div>

          </div>

          <!-- Vínculos (automáticos + manuais) -->
          <div class="card space-y-2 border-l-4 border-l-orange-500">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-300">Vínculos</h3>
              <button @click="abrirModalVinculo()"
                      class="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition-colors">
                + Adicionar
              </button>
            </div>

            <!-- Seção 1: Vínculos em Abordagem -->
            <div x-show="pessoa.relacionamentos?.length > 0" class="space-y-1">
              <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Vínculos em Abordagem (<span x-text="pessoa.relacionamentos.length"></span>)
              </p>
              <div class="space-y-2">
                <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
                  <div @click="viewPessoa(rel.pessoa_id)"
                       class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-orange-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
                    <div class="flex items-center gap-2">
                      <template x-if="rel.foto_principal_url">
                        <img :src="rel.foto_principal_url"
                             class="w-8 h-8 rounded-full object-cover border-2 border-slate-600 shrink-0"
                             loading="lazy">
                      </template>
                      <template x-if="!rel.foto_principal_url">
                        <div class="w-8 h-8 rounded-full bg-slate-700 border-2 border-slate-600 flex items-center justify-center text-slate-400 shrink-0">
                          <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                          </svg>
                        </div>
                      </template>
                      <span class="text-sm text-slate-300" x-text="rel.nome"></span>
                    </div>
                    <div class="text-right">
                      <span class="text-xs text-blue-400 font-medium" x-text="rel.frequencia + 'x juntos'"></span>
                      <p x-show="rel.ultima_vez" class="text-[10px] text-slate-500"
                         x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Separador (só quando ambas as seções têm itens) -->
            <div x-show="pessoa.relacionamentos?.length > 0 && vinculosManuais.length > 0"
                 class="border-t border-slate-700/50"></div>

            <!-- Seção 2: Vínculos Manuais -->
            <div x-show="vinculosManuais.length > 0" class="space-y-1">
              <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Vínculos Manuais (<span x-text="vinculosManuais.length"></span>)
              </p>
              <div class="space-y-2">
                <template x-for="vm in vinculosManuais" :key="vm.id">
                  <div @click="viewPessoa(vm.pessoa_vinculada_id)"
                       class="flex items-start justify-between border border-slate-700/40 border-l-4 border-l-purple-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
                    <div class="flex items-start gap-2">
                      <template x-if="vm.foto_principal_url">
                        <img :src="vm.foto_principal_url"
                             class="w-8 h-8 rounded-full object-cover border-2 border-slate-600 shrink-0 mt-0.5"
                             loading="lazy">
                      </template>
                      <template x-if="!vm.foto_principal_url">
                        <div class="w-8 h-8 rounded-full bg-slate-700 border-2 border-slate-600 flex items-center justify-center text-slate-400 shrink-0 mt-0.5">
                          <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                          </svg>
                        </div>
                      </template>
                      <div>
                        <span class="text-sm text-slate-300" x-text="vm.nome"></span>
                        <p class="text-xs text-purple-400 font-semibold mt-0.5" x-text="vm.tipo"></p>
                        <p x-show="vm.descricao"
                           class="text-xs text-slate-400 italic mt-0.5"
                           x-text="'&quot;' + vm.descricao + '&quot;'"></p>
                      </div>
                    </div>
                    <div class="flex flex-col items-end gap-1 shrink-0 ml-2">
                      <span x-show="vm.criado_em" class="text-[10px] text-slate-500"
                            x-text="new Date(vm.criado_em).toLocaleDateString('pt-BR')"></span>
                      <button @click.stop="removerVinculo(vm.id)"
                              class="text-slate-500 hover:text-red-400 transition-colors"
                              title="Remover vínculo">
                        <svg class="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
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
                 class="text-xs text-slate-500 text-center py-2">
              Nenhum vínculo cadastrado
            </div>
          </div>

          <!-- Histórico de abordagens -->
          <div x-show="abordagens.length > 0" class="card space-y-2 border-l-4 border-l-purple-600">
            <h3 class="text-sm font-semibold text-slate-300">
              Histórico de Abordagens (<span x-text="abordagens.length"></span>)
            </h3>
            <div class="space-y-3">
              <template x-for="(ab, idx) in abordagens" :key="ab.id">
                <div class="border border-slate-700/40 border-l-4 rounded-lg p-3 space-y-2" :class="PALETTE[idx % PALETTE.length]">
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <span class="text-xs font-medium text-blue-400" x-text="'#' + ab.id"></span>
                    </div>
                    <span x-show="ab.criado_em" class="text-xs text-slate-500 shrink-0"
                          x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
                  </div>
                  <!-- Endereço da Abordagem -->
                  <div x-show="ab.endereco_texto" class="text-xs">
                    <span class="text-slate-500 font-medium">Endereço da Abordagem:</span>
                    <span class="text-slate-400 ml-1" x-text="ab.endereco_texto"></span>
                  </div>

                  <!-- Observação -->
                  <div x-show="ab.observacao" class="text-xs">
                    <span class="text-slate-500 font-medium">Observação:</span>
                    <span class="text-slate-300 ml-1" x-text="ab.observacao"></span>
                  </div>

                  <!-- Veículos desta abordagem -->
                  <template x-if="ab.veiculos?.length > 0">
                    <div class="pt-1">
                      <p class="text-[10px] font-semibold text-slate-500 mb-1.5">Veículos na Abordagem:</p>
                      <div class="flex flex-col gap-1.5">
                        <template x-for="v in ab.veiculos" :key="v.id">
                          <div class="text-xs text-slate-300">
                            <span class="font-mono font-semibold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
                            <template x-if="v.modelo || v.cor">
                              <span class="text-slate-400" x-text="' ' + [v.modelo, v.cor].filter(Boolean).join(' · ')"></span>
                            </template>
                            <template x-if="v.pessoa_id">
                              <span class="text-slate-500" x-text="' — ' + (ab.pessoas?.find(p => p.id === v.pessoa_id)?.nome || 'N/A')"></span>
                            </template>
                          </div>
                        </template>
                      </div>
                    </div>
                  </template>

                  <!-- Coabordados nesta abordagem -->
                  <template x-if="ab.pessoas?.filter(p => p.id !== ${pessoaId}).length > 0">
                    <div class="pt-1">
                      <p class="text-[10px] font-semibold text-slate-500 mb-1.5">Abordados juntos:</p>
                      <div class="flex flex-wrap gap-3">
                        <template x-for="p in ab.pessoas.filter(pp => pp.id !== ${pessoaId})" :key="p.id">
                          <div @click.stop="pessoaPreview = p"
                               class="flex flex-col items-center gap-1 cursor-pointer w-10">
                            <!-- Com foto -->
                            <template x-if="p.foto_principal_url">
                              <img :src="p.foto_principal_url"
                                   class="w-10 h-10 rounded-full object-cover border-2 border-slate-600 hover:border-blue-400 transition-colors"
                                   loading="lazy">
                            </template>
                            <!-- Sem foto: ícone silhueta -->
                            <template x-if="!p.foto_principal_url">
                              <div class="w-10 h-10 rounded-full bg-slate-700 border-2 border-slate-600 hover:border-blue-400 transition-colors flex items-center justify-center text-slate-400">
                                <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                                </svg>
                              </div>
                            </template>
                            <span class="text-[9px] text-slate-400 text-center leading-tight w-10 truncate"
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
          <div x-show="pontosComLocalizacao.length > 0" class="card space-y-2 border-l-4 border-l-teal-500">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-300">
                Mapa de Abordagens (<span x-text="pontosComLocalizacao.length"></span>)
              </h3>
              <div class="flex gap-1">
                <button
                  @click="toggleModoMapa('marcadores')"
                  :aria-pressed="modoMapa === 'marcadores'"
                  class="text-xs px-2 py-1 rounded transition-colors"
                  :class="modoMapa === 'marcadores' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'"
                >
                  Marcadores
                </button>
                <button
                  @click="toggleModoMapa('calor')"
                  :aria-pressed="modoMapa === 'calor'"
                  class="text-xs px-2 py-1 rounded transition-colors"
                  :class="modoMapa === 'calor' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'"
                >
                  Calor
                </button>
              </div>
            </div>
            <div
              id="mapa-pessoa-${pessoaId}"
              class="w-full h-[350px] rounded-lg bg-slate-800 z-[1]"
            ></div>
          </div>
        </div>
      </template>

      <!-- Erro -->
      <p x-show="erro" class="text-red-400 text-sm" x-text="erro"></p>
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

    async load() {
      try {
        // Buscar pessoa com detalhes
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.vinculosManuais = this.pessoa.vinculos_manuais || [];

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
        // Mapa veiculo_id → primeira foto do veículo
        const mapaFotos = {};
        for (const foto of fotosPlanas) {
          if (foto.veiculo_id && !mapaFotos[foto.veiculo_id]) {
            mapaFotos[foto.veiculo_id] = foto;
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
      // x-if já renderizou o conteúdo, mas aguarda Alpine processar o DOM
      await this.$nextTick();
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
      if (appEl?._x_dataStack) appEl._x_dataStack[0].navigate("consulta");
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
          data_nascimento: this.novaPessoaForm.data_nascimento || undefined,
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

    onNovaFotoSelected(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
      this.novaFotoFile = file;
      this.novaFotoPreviewUrl = URL.createObjectURL(file);
    },

    async uploadNovaFoto() {
      if (!this.novaFotoFile) return;
      this.uploadandoFoto = true;
      try {
        await api.uploadFile("/fotos/upload", this.novaFotoFile, {
          tipo: "rosto",
          pessoa_id: this.pessoaId,
        });
        // Recarregar lista de fotos
        this.fotos = await api.get(`/fotos/pessoa/${this.pessoaId}`);
        // Limpar estado
        if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
        this.novaFotoFile = null;
        this.novaFotoPreviewUrl = "";
        showToast("Foto adicionada com sucesso!", "success");
      } catch (err) {
        showToast(err?.message || "Erro ao enviar foto", "error");
      } finally {
        this.uploadandoFoto = false;
      }
    },
  };
}
