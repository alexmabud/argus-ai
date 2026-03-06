/**
 * Página de assistente RAG — Argus AI.
 *
 * Interface de chat com IA para geração de relatórios e consultas
 * operacionais usando Retrieval-Augmented Generation. Suporta slash
 * commands acionados ao digitar "/" no campo de entrada, exibindo
 * um menu de atalhos disponíveis.
 */

/** Lista de slash commands disponíveis no assistente. */
const SLASH_COMMANDS = [
  {
    cmd: "/relatorio",
    label: "/relatorio <id>",
    desc: "Gerar relatório completo de uma abordagem",
    exemplo: "/relatorio 42",
  },
  {
    cmd: "/buscar",
    label: "/buscar <texto>",
    desc: "Buscar ocorrências similares por texto",
    exemplo: "/buscar furto residência",
  },
  {
    cmd: "/resumo",
    label: "/resumo <id>",
    desc: "Resumo rápido de uma abordagem",
    exemplo: "/resumo 10",
  },
  {
    cmd: "/legislacao",
    label: "/legislacao <termo>",
    desc: "Buscar artigos de lei relacionados",
    exemplo: "/legislacao receptação",
  },
  {
    cmd: "/ajuda",
    label: "/ajuda",
    desc: "Listar todos os comandos disponíveis",
    exemplo: "/ajuda",
  },
];

/**
 * Renderiza o HTML da página do assistente RAG.
 *
 * @returns {string} HTML da página como string para injeção no DOM.
 */
function renderRagRelatorio() {
  return `
    <div x-data="ragRelatorioPage()" x-init="init()" class="flex flex-col h-full" style="height: calc(100vh - 8rem)">
      <h2 class="text-lg font-bold text-slate-100 mb-3 shrink-0">Assistente IA</h2>

      <!-- Histórico de mensagens -->
      <div x-ref="msgContainer"
           class="flex-1 overflow-y-auto space-y-3 mb-3 pr-1">

        <!-- Mensagem de boas-vindas -->
        <template x-if="mensagens.length === 0">
          <div class="text-center py-8 space-y-2">
            <p class="text-slate-400 text-sm">Assistente de relatórios operacionais.</p>
            <p class="text-slate-500 text-xs">Digite <span class="font-mono text-blue-400">/ajuda</span> para ver os comandos disponíveis.</p>
          </div>
        </template>

        <template x-for="(msg, i) in mensagens" :key="i">
          <div :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
            <div :class="msg.role === 'user'
                   ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-[85%] text-sm'
                   : 'bg-slate-700 text-slate-100 rounded-2xl rounded-tl-sm px-4 py-2 max-w-[90%] text-sm'">
              <!-- Conteúdo da mensagem -->
              <template x-if="msg.role === 'assistant' && msg.loading">
                <div class="flex items-center gap-2">
                  <span class="spinner" style="width:14px;height:14px;border-width:2px"></span>
                  <span class="text-slate-400 text-xs">Gerando...</span>
                </div>
              </template>
              <template x-if="!(msg.role === 'assistant' && msg.loading)">
                <div>
                  <pre class="whitespace-pre-wrap font-sans" x-text="msg.texto"></pre>
                  <!-- Fontes -->
                  <template x-if="msg.fontes">
                    <div class="mt-2 pt-2 border-t border-slate-600">
                      <p class="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mb-1">Fontes</p>
                      <template x-for="f in (msg.fontes.ocorrencias_usadas || [])" :key="f">
                        <span class="inline-block text-[10px] bg-slate-600 text-slate-300 rounded px-1.5 py-0.5 mr-1 mb-1" x-text="'BO ' + f"></span>
                      </template>
                      <template x-for="f in (msg.fontes.legislacao_usada || [])" :key="f">
                        <span class="inline-block text-[10px] bg-indigo-900 text-indigo-300 rounded px-1.5 py-0.5 mr-1 mb-1" x-text="f"></span>
                      </template>
                    </div>
                  </template>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- Slash command menu -->
      <div x-show="showCmds" x-cloak
           class="bg-slate-800 border border-slate-600 rounded-xl mb-2 overflow-hidden shadow-xl shrink-0">
        <p class="text-[10px] text-slate-500 uppercase tracking-widest px-3 pt-2 pb-1 font-semibold">Comandos</p>
        <template x-for="(c, i) in cmdsFiltrados" :key="c.cmd">
          <button
            @click="selecionarCmd(c)"
            :class="i === cmdIdx ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-slate-700'"
            class="w-full text-left px-3 py-2 flex items-center justify-between transition-colors">
            <div>
              <span class="font-mono text-sm font-semibold" x-text="c.label"></span>
              <p class="text-xs mt-0.5"
                 :class="i === cmdIdx ? 'text-blue-200' : 'text-slate-400'"
                 x-text="c.desc"></p>
            </div>
            <span class="font-mono text-[10px] shrink-0 ml-3"
                  :class="i === cmdIdx ? 'text-blue-200' : 'text-slate-500'"
                  x-text="c.exemplo"></span>
          </button>
        </template>
        <template x-if="cmdsFiltrados.length === 0">
          <p class="px-3 py-2 text-xs text-slate-500">Nenhum comando encontrado.</p>
        </template>
      </div>

      <!-- Input -->
      <div class="shrink-0 relative">
        <textarea
          x-ref="input"
          x-model="texto"
          @input="onInput()"
          @keydown="onKeydown($event)"
          @keydown.enter.prevent="enviar()"
          placeholder="Digite uma mensagem ou / para ver comandos..."
          rows="2"
          class="w-full resize-none pr-12 py-3 text-sm rounded-xl"
          style="min-height: 52px; max-height: 120px;"
          :disabled="carregando"
        ></textarea>
        <button
          @click="enviar()"
          :disabled="!texto.trim() || carregando"
          class="absolute right-2 bottom-2 p-2 rounded-lg bg-blue-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
          </svg>
        </button>
      </div>
    </div>
  `;
}

/**
 * Componente Alpine.js da página do assistente RAG.
 *
 * Gerencia histórico de mensagens, detecção de slash commands,
 * navegação no menu de comandos via teclado e envio de queries
 * para a API de RAG.
 *
 * @returns {object} Estado e métodos Alpine.js do componente.
 */
function ragRelatorioPage() {
  return {
    texto: "",
    mensagens: [],
    carregando: false,
    showCmds: false,
    cmdIdx: 0,
    _todosComandos: SLASH_COMMANDS,

    /** Comandos filtrados conforme o texto digitado após "/". */
    get cmdsFiltrados() {
      const termo = this.texto.trim().toLowerCase();
      if (!termo.startsWith("/")) return this._todosComandos;
      const filtro = termo.slice(1);
      if (!filtro) return this._todosComandos;
      return this._todosComandos.filter(
        (c) => c.cmd.slice(1).startsWith(filtro) || c.desc.toLowerCase().includes(filtro)
      );
    },

    init() {
      // Foco automático no input
      this.$nextTick(() => {
        if (this.$refs.input) this.$refs.input.focus();
      });
    },

    /**
     * Trata o evento de input no textarea.
     * Exibe o menu de slash commands ao detectar "/" no início da mensagem.
     */
    onInput() {
      const val = this.texto.trim();
      this.showCmds = val.startsWith("/");
      this.cmdIdx = 0;
    },

    /**
     * Trata navegação por teclado no menu de slash commands.
     * Setas ↑/↓ navegam entre opções; Tab/Enter seleciona; Escape fecha.
     *
     * @param {KeyboardEvent} e - Evento de teclado.
     */
    onKeydown(e) {
      if (!this.showCmds) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        this.cmdIdx = Math.min(this.cmdIdx + 1, this.cmdsFiltrados.length - 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.cmdIdx = Math.max(this.cmdIdx - 1, 0);
      } else if (e.key === "Tab") {
        e.preventDefault();
        if (this.cmdsFiltrados[this.cmdIdx]) {
          this.selecionarCmd(this.cmdsFiltrados[this.cmdIdx]);
        }
      } else if (e.key === "Escape") {
        this.showCmds = false;
      }
    },

    /**
     * Preenche o input com o comando selecionado e fecha o menu.
     *
     * @param {object} cmd - Objeto do comando selecionado.
     */
    selecionarCmd(cmd) {
      this.texto = cmd.exemplo + " ";
      this.showCmds = false;
      this.$nextTick(() => {
        if (this.$refs.input) {
          this.$refs.input.focus();
          // Cursor ao final
          const len = this.texto.length;
          this.$refs.input.setSelectionRange(len, len);
        }
      });
    },

    /**
     * Envia a mensagem atual para o backend e exibe a resposta.
     * Processa slash commands especiais antes de enviar para a API.
     */
    async enviar() {
      const msg = this.texto.trim();
      if (!msg || this.carregando) return;

      // Fechar menu de comandos
      this.showCmds = false;
      this.texto = "";
      this.carregando = true;

      // Adicionar mensagem do usuário
      this.mensagens.push({ role: "user", texto: msg });
      await this.$nextTick();
      this._scrollToBottom();

      // Placeholder da resposta
      const idx = this.mensagens.length;
      this.mensagens.push({ role: "assistant", texto: "", loading: true, fontes: null });
      await this.$nextTick();
      this._scrollToBottom();

      try {
        const resposta = await this._executarComando(msg);
        this.mensagens[idx] = {
          role: "assistant",
          texto: resposta.texto,
          loading: false,
          fontes: resposta.fontes || null,
        };
      } catch (err) {
        this.mensagens[idx] = {
          role: "assistant",
          texto: "Erro ao processar sua solicitação. Tente novamente.",
          loading: false,
          fontes: null,
        };
      } finally {
        this.carregando = false;
        await this.$nextTick();
        this._scrollToBottom();
      }
    },

    /**
     * Interpreta e executa o comando ou mensagem enviada.
     * Roteia para o endpoint correto conforme o slash command.
     *
     * @param {string} msg - Texto completo enviado pelo usuário.
     * @returns {Promise<{texto: string, fontes: object|null}>} Resposta formatada.
     */
    async _executarComando(msg) {
      const partes = msg.trim().split(/\s+/);
      const cmd = partes[0].toLowerCase();
      const args = partes.slice(1).join(" ");

      if (cmd === "/ajuda") {
        return { texto: this._textoAjuda(), fontes: null };
      }

      if (cmd === "/relatorio") {
        const id = parseInt(args, 10);
        if (!id) return { texto: "Uso: /relatorio <id_abordagem>\nExemplo: /relatorio 42", fontes: null };
        const r = await api.post(`/rag/relatorio`, { abordagem_id: id, instrucao: "" });
        return { texto: r.relatorio, fontes: r.fontes };
      }

      if (cmd === "/resumo") {
        const id = parseInt(args, 10);
        if (!id) return { texto: "Uso: /resumo <id_abordagem>\nExemplo: /resumo 10", fontes: null };
        const r = await api.post(`/rag/relatorio`, {
          abordagem_id: id,
          instrucao: "Gere um resumo curto em 3 linhas, destacando: local, envolvidos e desfecho.",
        });
        return { texto: r.relatorio, fontes: r.fontes };
      }

      if (cmd === "/buscar") {
        if (!args) return { texto: "Uso: /buscar <texto>\nExemplo: /buscar furto residência", fontes: null };
        const r = await api.get(`/rag/buscar?q=${encodeURIComponent(args)}`);
        if (!r.ocorrencias || r.ocorrencias.length === 0) {
          return { texto: "Nenhuma ocorrência similar encontrada.", fontes: null };
        }
        const linhas = r.ocorrencias.map(
          (o, i) => `${i + 1}. BO ${o.numero} (sim: ${o.similaridade})\n   ${(o.texto || "").slice(0, 150)}...`
        );
        return { texto: "Ocorrências similares:\n\n" + linhas.join("\n\n"), fontes: null };
      }

      if (cmd === "/legislacao") {
        if (!args) return { texto: "Uso: /legislacao <termo>\nExemplo: /legislacao receptação", fontes: null };
        const r = await api.get(`/rag/legislacao?q=${encodeURIComponent(args)}`);
        if (!r.artigos || r.artigos.length === 0) {
          return { texto: "Nenhum artigo encontrado para esse termo.", fontes: null };
        }
        const linhas = r.artigos.map(
          (a) => `• ${a.lei} art. ${a.artigo} — ${a.nome}\n  ${(a.texto || "").slice(0, 200)}`
        );
        return { texto: "Legislação relacionada:\n\n" + linhas.join("\n\n"), fontes: null };
      }

      // Mensagem livre — envia como consulta RAG genérica
      const r = await api.post(`/rag/chat`, { mensagem: msg });
      return { texto: r.resposta || r.texto || "Sem resposta.", fontes: r.fontes || null };
    },

    /**
     * Gera o texto de ajuda listando todos os slash commands.
     *
     * @returns {string} Texto formatado com todos os comandos.
     */
    _textoAjuda() {
      const linhas = SLASH_COMMANDS.map(
        (c) => `${c.label}\n  ${c.desc}\n  Exemplo: ${c.exemplo}`
      );
      return "Comandos disponíveis:\n\n" + linhas.join("\n\n");
    },

    /** Rola o container de mensagens até o final. */
    _scrollToBottom() {
      const el = this.$refs.msgContainer;
      if (el) el.scrollTop = el.scrollHeight;
    },
  };
}
