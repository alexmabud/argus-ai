/**
 * Página de upload de ocorrência (PDF) — Argus AI.
 *
 * Upload de boletim de ocorrência em PDF para processamento
 * assíncrono (extração de texto + embedding via arq worker).
 */
function renderOcorrenciaUpload() {
  return `
    <div x-data="ocorrenciaUploadPage()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Upload de Ocorrência</h2>

      <div class="card space-y-4">
        <!-- Número da ocorrência -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">Número RAP (Registro de Ocorrência PMDF)</label>
          <input type="text" x-model="numero" placeholder="Ex: RAP 2026/000123">
        </div>

        <!-- Abordagem vinculada -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">ID da Abordagem (opcional)</label>
          <input type="number" x-model="abordagemId" placeholder="ID da abordagem vinculada">
        </div>

        <!-- Arquivo PDF -->
        <div>
          <label class="block text-sm text-slate-300 mb-1">Arquivo PDF</label>
          <input type="file" accept="application/pdf" @change="onFileSelected($event)"
                 class="text-sm text-slate-400">
          <p x-show="file" class="text-xs text-slate-500 mt-1" x-text="file?.name + ' (' + formatSize(file?.size) + ')'"></p>
        </div>
      </div>

      <!-- Submit -->
      <button @click="submit()" class="btn btn-primary" :disabled="!file || !numero || submitting">
        <span x-show="!submitting">Enviar Ocorrência</span>
        <span x-show="submitting" class="flex items-center gap-2">
          <span class="spinner"></span> Enviando...
        </span>
      </button>

      <p x-show="sucesso" class="text-sm text-green-400" x-text="sucesso"></p>
      <p x-show="erro" class="text-sm text-red-400" x-text="erro"></p>

      <!-- Busca de ocorrências -->
      <div class="mt-6 card space-y-3">
        <h3 class="text-sm font-semibold text-slate-300">Buscar Ocorrência</h3>

        <div>
          <label class="block text-xs text-slate-400 mb-1">Nome do abordado</label>
          <input type="text" x-model="buscaNome" placeholder="Ex: Carlos Eduardo Souza"
                 class="w-full">
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Número RAP</label>
            <input type="text" x-model="buscaRap" placeholder="Ex: 2026/000123">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Data</label>
            <input type="date" x-model="buscaData">
          </div>
        </div>

        <button @click="buscar()" class="btn btn-primary w-full" :disabled="buscando">
          <span x-show="!buscando">Buscar</span>
          <span x-show="buscando" class="flex items-center justify-center gap-2">
            <span class="spinner"></span> Buscando...
          </span>
        </button>

        <div x-show="resultadosBusca !== null">
          <p x-show="resultadosBusca !== null && resultadosBusca.length === 0"
             class="text-xs text-slate-500 text-center py-2">Nenhuma ocorrência encontrada.</p>
          <div class="space-y-2">
            <template x-for="oc in (resultadosBusca || [])" :key="oc.id">
              <div class="card flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="oc.numero_ocorrencia"></p>
                  <p class="text-xs text-slate-500"
                     x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs px-2 py-0.5 rounded-full"
                        :class="oc.processada ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'"
                        x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
                  <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener"
                     class="btn btn-secondary text-xs px-3 py-1">Abrir PDF</a>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Lista de ocorrências recentes -->
      <div class="mt-6">
        <h3 class="text-sm font-semibold text-slate-300 mb-3">Ocorrências Recentes</h3>
        <div x-show="loadingList" class="flex justify-center py-4"><span class="spinner"></span></div>
        <div class="space-y-2">
          <template x-for="oc in ocorrencias" :key="oc.id">
            <div class="card">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="oc.numero_ocorrencia"></p>
                  <p class="text-xs text-slate-500" x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs px-2 py-0.5 rounded-full"
                        :class="oc.processada ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'"
                        x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
                  <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener"
                     class="btn btn-secondary text-xs px-3 py-1">Abrir PDF</a>
                </div>
              </div>
            </div>
          </template>
        </div>
        <p x-show="!loadingList && ocorrencias.length === 0" class="text-xs text-slate-500 text-center py-4">
          Nenhuma ocorrência cadastrada.
        </p>
      </div>
    </div>
  `;
}

function ocorrenciaUploadPage() {
  return {
    numero: "",
    abordagemId: null,
    file: null,
    submitting: false,
    sucesso: null,
    erro: null,
    ocorrencias: [],
    loadingList: true,
    buscaNome: "",
    buscaRap: "",
    buscaData: "",
    buscando: false,
    resultadosBusca: null,

    async init() {
      await this.loadList();
    },

    onFileSelected(event) {
      this.file = event.target.files[0] || null;
    },

    formatSize(bytes) {
      if (!bytes) return "0 B";
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / 1048576).toFixed(1) + " MB";
    },

    async submit() {
      this.submitting = true;
      this.sucesso = null;
      this.erro = null;

      try {
        const form = new FormData();
        form.append("arquivo_pdf", this.file);
        form.append("numero_ocorrencia", this.numero);
        if (this.abordagemId) form.append("abordagem_id", this.abordagemId);

        await api.request("POST", "/ocorrencias/", form);
        this.sucesso = `Ocorrência ${this.numero} enviada! Processamento em andamento.`;
        this.numero = "";
        this.file = null;
        this.abordagemId = null;
        await this.loadList();
      } catch (err) {
        this.erro = err.message || "Erro ao enviar ocorrência.";
      } finally {
        this.submitting = false;
      }
    },

    async loadList() {
      this.loadingList = true;
      try {
        this.ocorrencias = await api.get("/ocorrencias/?limit=10");
      } catch {
        this.ocorrencias = [];
      } finally {
        this.loadingList = false;
      }
    },

    async buscar() {
      if (!this.buscaNome && !this.buscaRap && !this.buscaData) return;
      this.erro = null;
      this.resultadosBusca = null;
      this.buscando = true;
      try {
        const params = new URLSearchParams();
        if (this.buscaNome) params.append("nome", this.buscaNome);
        if (this.buscaRap) params.append("rap", this.buscaRap);
        if (this.buscaData) params.append("data", this.buscaData);
        this.resultadosBusca = await api.get(`/ocorrencias/buscar?${params}`);
      } catch (err) {
        this.resultadosBusca = null;
        this.erro = err.message || "Erro ao buscar ocorrências.";
      } finally {
        this.buscando = false;
      }
    },
  };
}
