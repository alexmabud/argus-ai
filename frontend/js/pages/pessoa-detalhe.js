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
          <div x-show="fotos.length > 0" class="card space-y-2 border-l-4 border-l-amber-500">
            <h3 class="text-sm font-semibold text-slate-300">
              Fotos (<span x-text="fotos.length"></span>)
            </h3>
            <div class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <div>
                  <div class="relative">
                    <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                         @click="fotoAmpliada = foto.arquivo_url">
                    <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                          x-text="foto.tipo || 'foto'"></span>
                  </div>
                  <p class="text-xs text-slate-400 text-center mt-1"
                     x-show="foto.criado_em"
                     x-text="foto.criado_em ? new Date(foto.criado_em).toLocaleDateString('pt-BR') : ''"></p>
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
          <div x-show="veiculos.length > 0 || fotosVeiculos.length > 0" class="card space-y-3 border-l-4 border-l-emerald-500">
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
                    </div>
                    <span x-show="v.criado_em" class="text-xs text-slate-500 shrink-0"
                          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
                </div>
              </template>
            </div>

            <!-- Fotos de veículos -->
            <div x-show="fotosVeiculos.length > 0" class="space-y-2">
              <p class="text-xs font-semibold text-slate-500">
                Fotos de Veículos Vinculados ao Abordado (<span x-text="fotosVeiculos.length"></span>)
              </p>
              <div class="grid grid-cols-3 gap-2">
                <template x-for="foto in fotosVeiculos" :key="foto.id">
                  <div>
                    <div class="relative">
                      <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                           @click="fotoAmpliada = foto.arquivo_url">
                      <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                            x-text="foto.tipo || 'foto'"></span>
                    </div>
                    <p class="text-xs text-slate-400 text-center mt-1"
                       x-show="foto.criado_em"
                       x-text="foto.criado_em ? new Date(foto.criado_em).toLocaleDateString('pt-BR') : ''"></p>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Relacionamentos (vínculos) -->
          <div x-show="pessoa.relacionamentos?.length > 0" class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">
              Vínculos (<span x-text="pessoa.relacionamentos.length"></span>)
            </h3>
            <div class="space-y-2">
              <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
                <div @click="viewPessoa(rel.pessoa_id)" class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-orange-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
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
                      <span x-show="ab.data_hora" class="text-xs text-slate-400 ml-2"
                            x-text="'Data da Abordagem: ' + new Date(ab.data_hora).toLocaleString('pt-BR')"></span>
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

                  <!-- Veículos nesta abordagem -->
                  <div x-show="ab.veiculos?.length > 0" class="space-y-1">
                    <template x-for="av in ab.veiculos" :key="av.id">
                      <div class="text-xs text-slate-400">
                        <span class="text-slate-500 font-medium">Veículo Vinculado à Abordagem:</span>
                        <span class="ml-1" x-text="[formatPlaca(av.placa), av.modelo, av.cor, av.ano].filter(Boolean).join(' · ')"></span>
                      </div>
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
    fotosVeiculos: [],
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

        // Carregar fotos de veículo/placa de todas as abordagens em paralelo
        const fotosPromises = abordagens.map(ab =>
          api.get(`/fotos/abordagem/${ab.id}`).catch(() => [])
        );
        const fotosResultados = await Promise.all(fotosPromises);
        const tiposVeiculo = ['veiculo', 'placa'];
        this.fotosVeiculos = fotosResultados
          .flat()
          .filter(f => tiposVeiculo.includes(f.tipo));

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
  };
}
