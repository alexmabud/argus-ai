/**
 * Página de nova abordagem — Argus AI.
 *
 * Formulário completo para registro de abordagem com busca/cadastro
 * de pessoas como primeiro passo, GPS automático, autocomplete de
 * veículos, captura de foto, entrada por voz e envio offline.
 */
function renderAbordagemNova() {
  return `
    <div x-data="abordagemForm()" x-init="initForm()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Nova Abordagem</h2>

      <!-- 1. Pessoas abordadas (primeiro campo) -->
      <div class="card space-y-3">
        <label class="text-sm font-medium text-slate-300 block">Pessoas abordadas</label>

        <div x-data="autocompleteComponent('pessoa')" class="relative">
          <input type="text" x-model="query" @input="onInput()" @focus="showDropdown = results.length > 0 || noResults"
                 placeholder="Buscar por nome ou CPF..." class="w-full">

          <!-- Dropdown resultados -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               class="absolute z-20 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg max-h-56 overflow-y-auto shadow-lg">

            <!-- Resultados encontrados -->
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('pessoa-selected', { selected: selected })"
                      class="w-full text-left px-3 py-2 hover:bg-slate-700 text-sm text-slate-200 border-b border-slate-700 last:border-0">
                <span x-text="getLabel(item)"></span>
                <span x-show="item.cpf_masked" class="text-xs text-slate-400 ml-2" x-text="item.cpf_masked"></span>
              </button>
            </template>

            <!-- Nenhum resultado -->
            <div x-show="noResults" class="px-3 py-3 text-sm text-slate-400">
              <p>Nenhuma pessoa encontrada.</p>
              <button @click="showDropdown = false; $dispatch('abrir-cadastro-pessoa', { query: query })"
                      class="mt-2 w-full text-left text-blue-400 hover:text-blue-300 font-medium">
                + Cadastrar novo abordado
              </button>
            </div>
          </div>

          <!-- Tags selecionados -->
          <div class="flex flex-wrap gap-2 mt-2">
            <template x-for="item in selected" :key="item.id">
              <span class="bg-blue-900/50 text-blue-300 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('pessoa-selected', { selected: selected })"
                        class="text-blue-400 hover:text-white">&times;</button>
              </span>
            </template>
          </div>
        </div>

        <!-- Botão para cadastrar sem buscar -->
        <button x-show="!showNovaPessoa" @click="showNovaPessoa = true"
                class="text-xs text-blue-400 hover:text-blue-300">
          + Adicionar pessoa não cadastrada
        </button>

        <!-- Formulário inline: cadastrar nova pessoa -->
        <div x-show="showNovaPessoa" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-slate-200">Cadastrar novo abordado</h3>
            <button @click="showNovaPessoa = false; novaPessoa = {nome:'',cpf:'',endereco:''}"
                    class="text-slate-400 hover:text-white text-xs">Cancelar</button>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Nome *</label>
            <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo" class="w-full">
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">CPF</label>
            <input type="text" x-model="novaPessoa.cpf" placeholder="000.000.000-00" maxlength="14" class="w-full">
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Endereço</label>
            <input type="text" x-model="novaPessoa.endereco" placeholder="Rua, número, bairro..." class="w-full">
          </div>

          <button @click="criarPessoa()" class="btn btn-primary text-sm" :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
            <span x-show="!salvandoPessoa">Salvar e adicionar</span>
            <span x-show="salvandoPessoa" class="flex items-center gap-2">
              <span class="spinner"></span> Salvando...
            </span>
          </button>
          <p x-show="erroPessoa" class="text-xs text-red-400" x-text="erroPessoa"></p>
        </div>
      </div>

      <!-- 2. GPS -->
      <div class="card space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-slate-300">Localização</span>
          <button @click="captureGPS()" class="text-xs text-blue-400 hover:text-blue-300" :disabled="gpsLoading">
            <span x-show="!gpsLoading">Atualizar GPS</span>
            <span x-show="gpsLoading">Obtendo...</span>
          </button>
        </div>
        <p x-show="endereco" class="text-sm text-slate-400" x-text="endereco"></p>
        <p x-show="!endereco && !gpsLoading" class="text-sm text-slate-500">GPS não capturado</p>
        <p x-show="latitude" class="text-xs text-slate-500" x-text="latitude?.toFixed(6) + ', ' + longitude?.toFixed(6)"></p>
      </div>

      <!-- 3. Observação -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-sm text-slate-300">Observação</label>
          <button x-show="voiceSupported" @click="toggleVoice()"
                  class="text-xs px-2 py-1 rounded"
                  :class="recording ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300'">
            <span x-text="recording ? 'Parar' : 'Voz'"></span>
          </button>
        </div>
        <textarea x-model="observacao" rows="3" placeholder="Descreva a abordagem..."></textarea>
      </div>

      <!-- 4. Veículos (autocomplete) -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-sm text-slate-300">Veículos</label>
          <button @click="showOCR = !showOCR" class="text-xs text-blue-400">OCR Placa</button>
        </div>

        <!-- OCR de placa -->
        <div x-show="showOCR" x-cloak class="mb-2">
          <div x-data="ocrPlacaComponent()" class="space-y-2">
            <input type="file" accept="image/*" capture="environment"
                   @change="processImage($event)" class="text-sm text-slate-400">
            <p x-show="placa" class="text-sm text-green-400" x-text="'Placa detectada: ' + placa"></p>
            <p x-show="processing" class="text-sm text-slate-400">Processando OCR...</p>
          </div>
        </div>

        <div x-data="autocompleteComponent('veiculo')" class="relative">
          <input type="text" x-model="query" @input="onInput()" @focus="showDropdown = results.length > 0"
                 placeholder="Buscar por placa..." class="w-full">

          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               class="absolute z-20 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg max-h-48 overflow-y-auto shadow-lg">
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('veiculo-selected', { selected: selected })"
                      class="w-full text-left px-3 py-2 hover:bg-slate-700 text-sm text-slate-200 border-b border-slate-700 last:border-0"
                      x-text="getLabel(item)">
              </button>
            </template>
          </div>

          <div class="flex flex-wrap gap-2 mt-2">
            <template x-for="item in selected" :key="item.id">
              <span class="bg-green-900/50 text-green-300 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <span x-text="getLabel(item)"></span>
                <button @click="remove(item.id); $dispatch('veiculo-selected', { selected: selected })"
                        class="text-green-400 hover:text-white">&times;</button>
              </span>
            </template>
          </div>
        </div>
      </div>

      <!-- 5. Foto (câmera) -->
      <div>
        <label class="text-sm text-slate-300 mb-1 block">Foto</label>
        <input type="file" accept="image/*" capture="environment"
               @change="onFotoSelected($event)"
               class="text-sm text-slate-400">
        <p x-show="fotoFile" class="text-xs text-slate-500 mt-1" x-text="fotoFile?.name"></p>
      </div>

      <!-- 6. Submit -->
      <div class="space-y-3 pt-2">
        <button @click="submit()" class="btn btn-primary" :disabled="submitting">
          <span x-show="!submitting">Registrar Abordagem</span>
          <span x-show="submitting" class="flex items-center gap-2">
            <span class="spinner"></span> Salvando...
          </span>
        </button>

        <p x-show="erro" class="text-sm text-red-400" x-text="erro"></p>
        <p x-show="sucesso" class="text-sm text-green-400" x-text="sucesso"></p>
      </div>
    </div>
  `;
}

function abordagemForm() {
  return {
    // GPS
    latitude: null,
    longitude: null,
    endereco: "",
    gpsLoading: false,

    // Formulário
    observacao: "",
    pessoaIds: [],
    veiculoIds: [],
    fotoFile: null,
    showOCR: false,
    submitting: false,
    erro: null,
    sucesso: null,

    // Voz
    recording: false,
    voiceSupported: typeof webkitSpeechRecognition !== "undefined" || typeof SpeechRecognition !== "undefined",

    // Cadastro nova pessoa
    showNovaPessoa: false,
    novaPessoa: { nome: "", cpf: "", endereco: "" },
    salvandoPessoa: false,
    erroPessoa: null,

    async initForm() {
      // Capturar GPS automaticamente
      this.captureGPS();

      // Escutar seleções de autocomplete
      this.$el.addEventListener("pessoa-selected", (e) => {
        this.pessoaIds = e.detail.selected.map((s) => s.id);
      });
      this.$el.addEventListener("veiculo-selected", (e) => {
        this.veiculoIds = e.detail.selected.map((s) => s.id);
      });

      // Escutar pedido de abrir cadastro (vindo do autocomplete)
      this.$el.addEventListener("abrir-cadastro-pessoa", (e) => {
        this.showNovaPessoa = true;
        // Preencher nome com o que foi buscado (se não for CPF)
        const q = e.detail?.query || "";
        if (q && !/^\d/.test(q)) {
          this.novaPessoa.nome = q;
        } else if (q && /^\d/.test(q)) {
          this.novaPessoa.cpf = q;
        }
      });
    },

    async criarPessoa() {
      const nome = this.novaPessoa.nome.trim();
      if (!nome) {
        this.erroPessoa = "Nome é obrigatório.";
        return;
      }

      this.salvandoPessoa = true;
      this.erroPessoa = null;

      try {
        // Criar pessoa
        const pessoaData = { nome };
        if (this.novaPessoa.cpf.trim()) {
          pessoaData.cpf = this.novaPessoa.cpf.trim();
        }

        const pessoa = await api.post("/pessoas/", pessoaData);

        // Criar endereço se preenchido
        if (this.novaPessoa.endereco.trim()) {
          await api.post(`/pessoas/${pessoa.id}/enderecos`, {
            endereco: this.novaPessoa.endereco.trim(),
          });
        }

        // Adicionar à lista de abordados
        this.pessoaIds.push(pessoa.id);

        // Atualizar tags do autocomplete
        const autocompleteEl = this.$el.querySelector("[x-data*='autocompleteComponent']");
        if (autocompleteEl?._x_dataStack) {
          autocompleteEl._x_dataStack[0].selected.push(pessoa);
        }

        // Reset formulário
        this.novaPessoa = { nome: "", cpf: "", endereco: "" };
        this.showNovaPessoa = false;
      } catch (err) {
        this.erroPessoa = err.message || "Erro ao cadastrar pessoa.";
      } finally {
        this.salvandoPessoa = false;
      }
    },

    async captureGPS() {
      this.gpsLoading = true;
      try {
        const loc = await getGPSLocation();
        this.latitude = loc.latitude;
        this.longitude = loc.longitude;
        this.endereco = loc.endereco_texto || "";
      } catch {
        this.endereco = "";
      } finally {
        this.gpsLoading = false;
      }
    },

    toggleVoice() {
      if (this.recording) {
        stopVoice();
        this.recording = false;
      } else {
        startVoice(
          (text, isFinal) => {
            if (isFinal) {
              this.observacao += (this.observacao ? " " : "") + text;
            }
          },
          () => { this.recording = false; }
        );
        this.recording = true;
      }
    },

    onFotoSelected(event) {
      this.fotoFile = event.target.files[0] || null;
    },

    async submit() {
      this.submitting = true;
      this.erro = null;
      this.sucesso = null;

      const payload = {
        data_hora: new Date().toISOString(),
        latitude: this.latitude,
        longitude: this.longitude,
        endereco_texto: this.endereco || null,
        observacao: this.observacao || null,
        origem: navigator.onLine ? "online" : "offline",
        pessoa_ids: this.pessoaIds,
        veiculo_ids: this.veiculoIds,
        passagens: [],
      };

      try {
        if (navigator.onLine) {
          const result = await api.post("/abordagens/", payload);

          // Upload foto se houver
          if (this.fotoFile && result.id) {
            await api.uploadFile("/fotos/upload", this.fotoFile, {
              tipo: "cena",
              abordagem_id: result.id,
              latitude: this.latitude,
              longitude: this.longitude,
            });
          }

          this.sucesso = `Abordagem #${result.id} registrada com sucesso!`;
        } else {
          // Salvar offline
          await enqueueSync("abordagem", payload);
          this.sucesso = "Abordagem salva na fila offline. Será sincronizada automaticamente.";
          // Atualizar contador de pendentes
          const appEl = document.querySelector("[x-data]");
          if (appEl?._x_dataStack) appEl._x_dataStack[0]._updateSyncCount();
        }

        // Reset form
        this.observacao = "";
        this.pessoaIds = [];
        this.veiculoIds = [];
        this.fotoFile = null;
      } catch (err) {
        this.erro = err.message || "Erro ao registrar abordagem.";
      } finally {
        this.submitting = false;
      }
    },
  };
}
