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
          <div class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">Dados Pessoais</h3>
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span class="text-slate-500">CPF:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.cpf || pessoa.cpf_masked || '—'"></span>
              </div>
              <div>
                <span class="text-slate-500">Nascimento:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.data_nascimento ? new Date(pessoa.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '—'"></span>
              </div>
              <div>
                <span class="text-slate-500">Abordagens:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.abordagens_count || 0"></span>
              </div>
              <div>
                <span class="text-slate-500">Cadastro:</span>
                <span class="text-slate-300 ml-1" x-text="new Date(pessoa.criado_em).toLocaleDateString('pt-BR')"></span>
              </div>
            </div>
            <div x-show="pessoa.observacoes" class="pt-1">
              <span class="text-xs text-slate-500">Obs:</span>
              <p class="text-xs text-slate-400" x-text="pessoa.observacoes"></p>
            </div>
          </div>

          <!-- Fotos -->
          <div x-show="fotos.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Fotos (<span x-text="fotos.length"></span>)
            </h3>
            <div class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <div class="relative">
                  <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                       @click="fotoAmpliada = foto.arquivo_url">
                  <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                        x-text="foto.tipo || 'foto'"></span>
                </div>
              </template>
            </div>
          </div>

          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
            <img :src="fotoAmpliada" class="max-w-full max-h-full rounded-lg">
          </div>

          <!-- Endereços -->
          <div x-show="pessoa.enderecos?.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Endereços (<span x-text="pessoa.enderecos.length"></span>)
            </h3>
            <div class="space-y-2">
              <template x-for="(end, idx) in pessoa.enderecos" :key="end.id">
                <div class="border-l-2 pl-3 py-1"
                     :class="idx === 0 ? 'border-blue-500' : 'border-slate-600'">
                  <p class="text-sm text-slate-300" x-text="formatEndereco(end)"></p>
                  <div class="flex gap-3 text-[10px] text-slate-500 mt-0.5">
                    <span x-show="end.data_inicio" x-text="'Desde ' + new Date(end.data_inicio + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="end.data_fim" x-text="'Até ' + new Date(end.data_fim + 'T00:00:00').toLocaleDateString('pt-BR')"></span>
                    <span x-show="idx === 0" class="text-blue-400 font-medium">Atual</span>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Veículos vinculados -->
          <div x-show="veiculos.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Veículos (<span x-text="veiculos.length"></span>)
            </h3>
            <div class="space-y-2">
              <template x-for="v in veiculos" :key="v.id">
                <div class="flex items-center gap-3 bg-slate-800/50 rounded-lg p-2">
                  <div>
                    <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="v.placa"></span>
                    <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
                       x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Relacionamentos (vínculos) -->
          <div x-show="pessoa.relacionamentos?.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Vínculos (<span x-text="pessoa.relacionamentos.length"></span>)
            </h3>
            <div class="space-y-2">
              <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
                <div @click="viewPessoa(rel.pessoa_id)" class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2 cursor-pointer hover:bg-slate-700/50">
                  <span class="text-sm text-slate-300" x-text="rel.nome"></span>
                  <div class="text-right">
                    <span class="text-xs text-blue-400 font-medium" x-text="rel.frequencia + 'x juntos'"></span>
                    <p x-show="rel.ultima_vez" class="text-[10px] text-slate-500"
                       x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Histórico de abordagens -->
          <div x-show="abordagens.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Histórico de Abordagens (<span x-text="abordagens.length"></span>)
            </h3>
            <div class="space-y-3">
              <template x-for="ab in abordagens" :key="ab.id">
                <div class="border border-slate-700 rounded-lg p-3 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-medium text-blue-400" x-text="'#' + ab.id"></span>
                    <span class="text-xs text-slate-400" x-text="new Date(ab.data_hora).toLocaleString('pt-BR')"></span>
                  </div>
                  <p x-show="ab.endereco_texto" class="text-xs text-slate-400" x-text="ab.endereco_texto"></p>
                  <p x-show="ab.observacao" class="text-xs text-slate-300" x-text="ab.observacao"></p>

                  <!-- Pessoas nesta abordagem -->
                  <div x-show="ab.pessoas?.length > 0" class="flex flex-wrap gap-1">
                    <template x-for="ap in ab.pessoas" :key="ap.id">
                      <span class="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
                            x-text="ap.nome"></span>
                    </template>
                  </div>

                  <!-- Veículos nesta abordagem -->
                  <div x-show="ab.veiculos?.length > 0" class="flex flex-wrap gap-1">
                    <template x-for="av in ab.veiculos" :key="av.id">
                      <span class="text-[10px] bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded font-mono"
                            x-text="av.placa"></span>
                    </template>
                  </div>
                </div>
              </template>
            </div>
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
    abordagens: [],
    veiculos: [],
    fotoAmpliada: null,
    loading: true,
    erro: null,

    async load() {
      try {
        // Buscar pessoa com detalhes
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);

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
    },

    async carregarAbordagens() {
      try {
        const abordagens = await api.get(`/pessoas/${pessoaId}/abordagens`);
        this.abordagens = abordagens;

        // Coletar veículos únicos de todas as abordagens
        const veiculosMap = {};
        for (const ab of abordagens) {
          for (const v of ab.veiculos || []) {
            veiculosMap[v.id] = v;
          }
        }
        this.veiculos = Object.values(veiculosMap);
      } catch { /* silencioso */ }
    },

    formatEndereco(end) {
      if (!end) return "";
      const parts = [end.endereco, end.bairro, end.cidade, end.estado].filter(Boolean);
      return parts.join(", ");
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
  };
}
