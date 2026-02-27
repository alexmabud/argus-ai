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
          <label class="block text-sm text-slate-300 mb-1">Número da Ocorrência (BO)</label>
          <input type="text" x-model="numero" placeholder="Ex: 2026/000123">
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
                <span class="text-xs px-2 py-0.5 rounded-full"
                      :class="oc.processada ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'"
                      x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
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
  };
}
