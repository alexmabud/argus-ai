/**
 * Página de upload de ocorrência (PDF) — Argus AI.
 *
 * Upload de boletim de ocorrência em PDF para processamento
 * assíncrono (extração de texto + embedding via arq worker).
 */
function renderOcorrenciaUpload() {
  return `
    <div x-data="ocorrenciaUploadPage()" style="display:flex;flex-direction:column;gap:20px;">

      <!-- Header -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.1em;margin:0;">
          UPLOAD DE OCORRENCIA
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;margin-top:4px;">
          DOCUMENTOS OPERACIONAIS
        </p>
      </div>

      <!-- Form Card -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">

        <!-- Número da ocorrência -->
        <div>
          <label class="login-field-label">Número RAP (Registro de Ocorrência PMDF)</label>
          <input type="text" x-model="numero" placeholder="Ex: RAP 2026/000123">
        </div>

        <!-- Abordagem vinculada -->
        <div>
          <label class="login-field-label">ID da Abordagem (opcional)</label>
          <input type="number" x-model="abordagemId" placeholder="ID da abordagem vinculada">
        </div>

        <!-- Data da ocorrência -->
        <div>
          <label class="login-field-label">Data da Ocorrência</label>
          <input type="text" x-model="dataOcorrencia"
                 @input="dataOcorrencia = formatarData($event.target.value)"
                 placeholder="DD/MM/AAAA" maxlength="10" required>
        </div>

        <!-- Arquivo PDF -->
        <div>
          <label class="login-field-label">Arquivo PDF</label>
          <input type="file" accept="application/pdf" @change="onFileSelected($event)"
                 style="font-size:14px;color:var(--color-text-muted);">
          <p x-show="file" style="font-size:12px;color:var(--color-text-dim);margin-top:4px;" x-text="file?.name + ' (' + formatSize(file?.size) + ')'"></p>
        </div>

        <!-- Envolvidos -->
        <div>
          <label class="login-field-label">Envolvidos</label>
          <div style="display:flex;gap:8px;">
            <input type="text" x-model="novoEnvolvido"
                   placeholder="Nome do envolvido"
                   @keydown.enter.prevent="adicionarEnvolvido()"
                   style="flex:1;">
            <button type="button" @click="adicionarEnvolvido()"
                    class="btn btn-secondary" style="width:auto;padding:0 12px;flex-shrink:0;">+ Adicionar</button>
          </div>
          <div x-show="envolvidos.length > 0" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">
            <template x-for="(nome, i) in envolvidos" :key="i">
              <span style="display:flex;align-items:center;gap:4px;font-size:12px;background:rgba(0,212,255,0.1);color:var(--color-primary);padding:2px 10px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);">
                <span x-text="nome"></span>
                <button type="button" @click="removerEnvolvido(i)"
                        style="color:var(--color-text-muted);cursor:pointer;line-height:1;margin-left:2px;background:none;border:none;font-size:14px;"
                        onmouseover="this.style.color='var(--color-danger)'"
                        onmouseout="this.style.color='var(--color-text-muted)'">&times;</button>
              </span>
            </template>
          </div>
        </div>
      </div>

      <!-- Submit -->
      <button @click="submit()" class="btn btn-primary" :disabled="!file || !numero || !dataOcorrencia || submitting">
        <span x-show="!submitting">Enviar Ocorrência</span>
        <span x-show="submitting" style="display:flex;align-items:center;gap:8px;">
          <span class="spinner"></span> Enviando...
        </span>
      </button>

      <p x-show="sucesso" style="font-size:14px;color:var(--color-success);" x-text="sucesso"></p>
      <p x-show="erro" style="font-size:14px;color:var(--color-danger);" x-text="erro"></p>

      <!-- Busca de ocorrências -->
      <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;margin-top:8px;">
        <h3 style="font-family:var(--font-display);font-size:12px;font-weight:600;color:var(--color-text);text-transform:uppercase;letter-spacing:0.08em;margin:0;">
          Buscar Ocorrência
        </h3>

        <div>
          <label class="login-field-label">Nome do abordado</label>
          <input type="text" x-model="buscaNome" placeholder="Ex: Carlos Eduardo Souza"
                 style="width:100%;">
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
          <div>
            <label class="login-field-label">Número RAP</label>
            <input type="text" x-model="buscaRap" placeholder="Ex: 2026/000123">
          </div>
          <div>
            <label class="login-field-label">Data</label>
            <input type="text" x-model="buscaData"
                   @input="buscaData = formatarData($event.target.value)"
                   placeholder="DD/MM/AAAA" maxlength="10">
          </div>
        </div>

        <button @click="buscar()" class="btn btn-primary" style="width:100%;" :disabled="buscando">
          <span x-show="!buscando">Buscar</span>
          <span x-show="buscando" style="display:flex;align-items:center;justify-content:center;gap:8px;">
            <span class="spinner"></span> Buscando...
          </span>
        </button>

        <div x-show="resultadosBusca !== null">
          <p x-show="resultadosBusca !== null && resultadosBusca.length === 0"
             style="font-size:12px;color:var(--color-text-dim);text-align:center;padding:8px 0;">Nenhuma ocorrência encontrada.</p>
          <div style="display:flex;flex-direction:column;gap:8px;">
            <template x-for="oc in (resultadosBusca || [])" :key="oc.id">
              <div class="glass-card" style="padding:12px;border-radius:4px;display:flex;align-items:center;justify-content:space-between;transition:box-shadow 0.2s ease;"
                   onmouseover="this.style.boxShadow='0 0 12px rgba(0,212,255,0.15)'"
                   onmouseout="this.style.boxShadow='none'">
                <div>
                  <p style="font-size:14px;font-weight:500;color:var(--color-text);font-family:var(--font-data);" x-text="oc.numero_ocorrencia"></p>
                  <p style="font-size:12px;color:var(--color-text-dim);"
                     x-text="'Ocorrido em ' + formatDate(oc.data_ocorrencia) + ' · Registrado em ' + formatDate(oc.criado_em)"></p>
                  <p x-show="oc.nomes_envolvidos && oc.nomes_envolvidos.length > 0"
                     style="font-size:12px;color:var(--color-text-muted);margin-top:2px;"
                     x-text="oc.nomes_envolvidos.join(' · ')"></p>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-size:12px;padding:2px 8px;border-radius:4px;"
                        :style="oc.processada
                          ? 'background:rgba(0,255,136,0.15);color:var(--color-success);'
                          : 'background:rgba(255,107,0,0.15);color:var(--color-danger);'"
                        x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
                  <template x-if="oc.arquivo_pdf_url">
                    <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener noreferrer"
                       :aria-label="'Abrir PDF da ocorrência ' + oc.numero_ocorrencia"
                       class="btn btn-secondary" style="font-size:12px;padding:4px 12px;">Abrir PDF</a>
                  </template>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Lista de ocorrências recentes -->
      <div style="margin-top:8px;">
        <h3 style="font-family:var(--font-display);font-size:12px;font-weight:600;color:var(--color-text);text-transform:uppercase;letter-spacing:0.08em;margin:0 0 12px 0;">
          Ocorrências Registradas
        </h3>
        <div x-show="loadingList" style="display:flex;justify-content:center;padding:16px 0;"><span class="spinner"></span></div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <template x-for="oc in ocorrencias" :key="oc.id">
            <div class="glass-card" style="padding:12px;border-radius:4px;transition:box-shadow 0.2s ease;"
                 onmouseover="this.style.boxShadow='0 0 12px rgba(0,212,255,0.15)'"
                 onmouseout="this.style.boxShadow='none'">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                  <p style="font-size:14px;font-weight:500;color:var(--color-text);font-family:var(--font-data);" x-text="oc.numero_ocorrencia"></p>
                  <p style="font-size:12px;color:var(--color-text-dim);"
                     x-text="'Ocorrido em ' + formatDate(oc.data_ocorrencia) + ' · Registrado em ' + formatDate(oc.criado_em)"></p>
                  <p x-show="oc.nomes_envolvidos && oc.nomes_envolvidos.length > 0"
                     style="font-size:12px;color:var(--color-text-muted);margin-top:2px;"
                     x-text="oc.nomes_envolvidos.join(' · ')"></p>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-size:12px;padding:2px 8px;border-radius:4px;"
                        :style="oc.processada
                          ? 'background:rgba(0,255,136,0.15);color:var(--color-success);'
                          : 'background:rgba(255,107,0,0.15);color:var(--color-danger);'"
                        x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
                  <template x-if="oc.arquivo_pdf_url">
                    <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener noreferrer"
                       :aria-label="'Abrir PDF da ocorrência ' + oc.numero_ocorrencia"
                       class="btn btn-secondary" style="font-size:12px;padding:4px 12px;">Abrir PDF</a>
                  </template>
                </div>
              </div>
            </div>
          </template>
        </div>
        <p x-show="!loadingList && ocorrencias.length === 0" style="font-size:12px;color:var(--color-text-dim);text-align:center;padding:16px 0;">
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
    dataOcorrencia: new Date().toLocaleDateString("pt-BR"),
    novoEnvolvido: "",
    envolvidos: [],
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

    formatDate(isoString) {
      if (!isoString) return "";
      // Suporta tanto "2026-03-07" (DATE) quanto "2026-03-07T..." (DATETIME)
      const d = new Date(isoString + (isoString.includes("T") ? "" : "T00:00:00"));
      return d.toLocaleDateString("pt-BR");
    },

    formatSize(bytes) {
      if (!bytes) return "0 B";
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / 1048576).toFixed(1) + " MB";
    },

    adicionarEnvolvido() {
      const nome = this.novoEnvolvido.trim();
      if (nome && !this.envolvidos.includes(nome)) {
        this.envolvidos.push(nome);
      }
      this.novoEnvolvido = "";
    },

    removerEnvolvido(index) {
      this.envolvidos.splice(index, 1);
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
        if (this.envolvidos.length > 0) {
          form.append("nomes_envolvidos", this.envolvidos.join("|"));
        }
        form.append("data_ocorrencia", parseDateBR(this.dataOcorrencia));

        await api.request("POST", "/ocorrencias/", form);
        this.sucesso = `Ocorrência ${this.numero} enviada! Processamento em andamento.`;
        this.numero = "";
        this.file = null;
        this.abordagemId = null;
        this.dataOcorrencia = new Date().toLocaleDateString("pt-BR");
        this.envolvidos = [];
        this.novoEnvolvido = "";
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
        this.ocorrencias = await api.get("/ocorrencias/?limit=100");
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
        const buscaDataISO = parseDateBR(this.buscaData);
        if (buscaDataISO) params.append("data", buscaDataISO);
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
