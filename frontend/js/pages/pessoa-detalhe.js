/**
 * Página de detalhe de pessoa — Argus AI.
 *
 * Exibe dados pessoais, fotos, endereços, relacionamentos
 * (vínculos com outras pessoas) e histórico de abordagens.
 */
function renderPessoaDetalhe(appState) {
  const pessoaId = appState._pessoaId;
  if (!pessoaId) {
    return `<p class="text-slate-400">Nenhuma pessoa selecionada.</p>`;
  }

  return `
    <div x-data="pessoaDetalhePage(${pessoaId})" x-init="load()" class="space-y-4">
      <!-- Loading -->
      <div x-show="loading" class="flex justify-center py-12">
        <span class="spinner"></span>
      </div>

      <!-- Conteúdo -->
      <template x-if="pessoa && !loading">
        <div class="space-y-4">
          <!-- Header -->
          <div class="flex items-start justify-between">
            <div>
              <button @click="goBack()" class="text-blue-400 text-sm mb-2">&larr; Voltar</button>
              <h2 class="text-xl font-bold text-slate-100" x-text="pessoa.nome"></h2>
              <p x-show="pessoa.apelido" class="text-slate-400 text-sm" x-text="'Apelido: ' + pessoa.apelido"></p>
            </div>
          </div>

          <!-- Dados pessoais -->
          <div class="card space-y-2">
            <h3 class="text-sm font-semibold text-slate-300">Dados Pessoais</h3>
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span class="text-slate-500">CPF:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.cpf_masked || '—'"></span>
              </div>
              <div>
                <span class="text-slate-500">Nascimento:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.data_nascimento ? new Date(pessoa.data_nascimento).toLocaleDateString('pt-BR') : '—'"></span>
              </div>
              <div class="col-span-2">
                <span class="text-slate-500">Abordagens:</span>
                <span class="text-slate-300 ml-1" x-text="pessoa.abordagens_count || 0"></span>
              </div>
            </div>
            <p x-show="pessoa.observacoes" class="text-xs text-slate-400 mt-2" x-text="pessoa.observacoes"></p>
          </div>

          <!-- Fotos -->
          <div x-show="fotos.length > 0" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Fotos</h3>
            <div class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <img :src="foto.arquivo_url" class="w-full h-24 object-cover rounded-lg" loading="lazy">
              </template>
            </div>
          </div>

          <!-- Endereços -->
          <div x-show="pessoa.enderecos?.length > 0" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Endereços</h3>
            <div class="space-y-2">
              <template x-for="end in pessoa.enderecos" :key="end.id">
                <div class="text-sm">
                  <p class="text-slate-300" x-text="end.endereco"></p>
                  <p class="text-xs text-slate-500" x-text="end.data_inicio ? 'Desde ' + new Date(end.data_inicio).toLocaleDateString('pt-BR') : ''"></p>
                </div>
              </template>
            </div>
          </div>

          <!-- Relacionamentos -->
          <div x-show="pessoa.relacionamentos?.length > 0" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Vínculos</h3>
            <div class="space-y-2">
              <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-300" x-text="rel.nome"></span>
                  <span class="text-xs text-slate-500" x-text="rel.frequencia + 'x juntos'"></span>
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
    loading: true,
    erro: null,

    async load() {
      try {
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        try {
          this.fotos = await api.get(`/fotos/pessoa/${pessoaId}`);
        } catch {
          this.fotos = [];
        }
      } catch (err) {
        this.erro = err.message || "Erro ao carregar pessoa.";
      } finally {
        this.loading = false;
      }
    },

    goBack() {
      const appEl = document.querySelector("[x-data]");
      if (appEl?.__x) appEl.__x.$data.navigate("consulta");
    },
  };
}
