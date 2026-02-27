/**
 * Página de geração de relatório via RAG — Argus AI.
 *
 * Seleciona abordagem, envia instrução opcional ao LLM,
 * e exibe relatório gerado com fontes (ocorrências + legislação).
 */
function renderRagRelatorio() {
  return `
    <div x-data="ragRelatorioPage()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Relatório com IA</h2>

      <div class="card space-y-4">
        <!-- ID da abordagem -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">ID da Abordagem</label>
          <input type="number" x-model="abordagemId" placeholder="Digite o ID da abordagem" min="1">
        </div>

        <!-- Instrução extra -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">Instrução adicional (opcional)</label>
          <textarea x-model="instrucao" rows="2"
                    placeholder="Ex: Foque nos antecedentes criminais e legislação aplicável..."></textarea>
        </div>
      </div>

      <!-- Gerar -->
      <button @click="gerar()" class="btn btn-primary" :disabled="!abordagemId || gerando">
        <span x-show="!gerando">Gerar Relatório</span>
        <span x-show="gerando" class="flex items-center gap-2">
          <span class="spinner"></span> Gerando com IA...
        </span>
      </button>

      <p x-show="erro" class="text-sm text-red-400" x-text="erro"></p>

      <!-- Resultado -->
      <template x-if="relatorio">
        <div class="space-y-4">
          <!-- Relatório -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Relatório Gerado</h3>
            <div class="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed" x-text="relatorio.relatorio"></div>
          </div>

          <!-- Fontes: Ocorrências -->
          <div x-show="relatorio.fontes_ocorrencias?.length > 0" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Fontes — Ocorrências</h3>
            <div class="space-y-1">
              <template x-for="(fonte, i) in relatorio.fontes_ocorrencias" :key="i">
                <p class="text-xs text-slate-400" x-text="fonte.numero_ocorrencia || ('Ocorrência #' + fonte.id)"></p>
              </template>
            </div>
          </div>

          <!-- Fontes: Legislação -->
          <div x-show="relatorio.fontes_legislacao?.length > 0" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Fontes — Legislação</h3>
            <div class="space-y-1">
              <template x-for="(fonte, i) in relatorio.fontes_legislacao" :key="i">
                <p class="text-xs text-slate-400" x-text="fonte.lei + ', Art. ' + fonte.artigo + ' — ' + fonte.nome"></p>
              </template>
            </div>
          </div>

          <!-- Métricas -->
          <div x-show="relatorio.metricas" class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Métricas</h3>
            <div class="grid grid-cols-2 gap-2 text-xs text-slate-400">
              <template x-for="(value, key) in relatorio.metricas" :key="key">
                <div>
                  <span class="text-slate-500" x-text="key + ': '"></span>
                  <span x-text="typeof value === 'number' ? value.toFixed(2) : value"></span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>

      <!-- Busca semântica rápida -->
      <div class="mt-8 border-t border-slate-700 pt-6">
        <h3 class="text-sm font-semibold text-slate-300 mb-3">Busca Semântica</h3>
        <div class="flex gap-2">
          <input type="text" x-model="buscaQuery" placeholder="Buscar em ocorrências e legislação..." class="flex-1">
          <button @click="buscar()" class="btn btn-secondary !w-auto px-4" :disabled="!buscaQuery || buscando">
            <span x-show="!buscando">Buscar</span>
            <span x-show="buscando" class="spinner"></span>
          </button>
        </div>

        <div x-show="buscaResults" class="mt-4 space-y-3">
          <template x-for="(oc, i) in buscaResults?.ocorrencias || []" :key="'oc-'+i">
            <div class="card">
              <p class="text-xs text-blue-400">Ocorrência</p>
              <p class="text-sm text-slate-300" x-text="oc.numero_ocorrencia"></p>
              <p x-show="oc.similaridade" class="text-xs text-slate-500" x-text="'Similaridade: ' + (oc.similaridade * 100).toFixed(0) + '%'"></p>
            </div>
          </template>
          <template x-for="(leg, i) in buscaResults?.legislacoes || []" :key="'leg-'+i">
            <div class="card">
              <p class="text-xs text-green-400">Legislação</p>
              <p class="text-sm text-slate-300" x-text="leg.lei + ', Art. ' + leg.artigo + ' — ' + leg.nome"></p>
              <p class="text-xs text-slate-400 mt-1 line-clamp-2" x-text="leg.texto"></p>
            </div>
          </template>
        </div>
      </div>
    </div>
  `;
}

function ragRelatorioPage() {
  return {
    abordagemId: null,
    instrucao: "",
    relatorio: null,
    gerando: false,
    erro: null,
    buscaQuery: "",
    buscaResults: null,
    buscando: false,

    async gerar() {
      this.gerando = true;
      this.erro = null;
      this.relatorio = null;

      try {
        const payload = {
          abordagem_id: parseInt(this.abordagemId),
        };
        if (this.instrucao.trim()) {
          payload.instrucao = this.instrucao.trim();
        }
        this.relatorio = await api.post("/rag/relatorio", payload);
      } catch (err) {
        this.erro = err.message || "Erro ao gerar relatório.";
      } finally {
        this.gerando = false;
      }
    },

    async buscar() {
      this.buscando = true;
      try {
        this.buscaResults = await api.post("/rag/busca", {
          query: this.buscaQuery,
          top_k: 5,
        });
      } catch (err) {
        showToast(err.message || "Erro na busca", "error");
      } finally {
        this.buscando = false;
      }
    },
  };
}
