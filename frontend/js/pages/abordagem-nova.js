/**
 * Página de nova abordagem — Argus AI.
 *
 * Formulário completo para registro de abordagem com GPS
 * automático, autocomplete de pessoas/veículos, captura
 * de foto, entrada por voz e envio offline.
 */
function renderAbordagemNova() {
  return `
    <div x-data="abordagemForm()" x-init="initForm()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Nova Abordagem</h2>

      <!-- GPS -->
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

      <!-- Observação -->
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

      <!-- Pessoas (autocomplete) -->
      <div>
        <label class="text-sm text-slate-300 mb-1 block">Pessoas abordadas</label>
        <div x-data="autocompleteComponent('pessoa')" class="relative">
          <input type="text" x-model="query" @input="onInput()" @focus="showDropdown = results.length > 0"
                 placeholder="Buscar por nome ou apelido..." class="w-full">

          <!-- Dropdown -->
          <div x-show="showDropdown" x-cloak @click.outside="showDropdown = false"
               class="absolute z-20 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg max-h-48 overflow-y-auto shadow-lg">
            <template x-for="item in results" :key="item.id">
              <button @click="select(item); $dispatch('pessoa-selected', { selected: selected })"
                      class="w-full text-left px-3 py-2 hover:bg-slate-700 text-sm text-slate-200 border-b border-slate-700 last:border-0"
                      x-text="getLabel(item)">
              </button>
            </template>
          </div>

          <!-- Selected tags -->
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
      </div>

      <!-- Veículos (autocomplete) -->
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

      <!-- Foto (câmera) -->
      <div>
        <label class="text-sm text-slate-300 mb-1 block">Foto</label>
        <input type="file" accept="image/*" capture="environment"
               @change="onFotoSelected($event)"
               class="text-sm text-slate-400">
        <p x-show="fotoFile" class="text-xs text-slate-500 mt-1" x-text="fotoFile?.name"></p>
      </div>

      <!-- Submit -->
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
    latitude: null,
    longitude: null,
    endereco: "",
    observacao: "",
    pessoaIds: [],
    veiculoIds: [],
    fotoFile: null,
    showOCR: false,
    gpsLoading: false,
    submitting: false,
    erro: null,
    sucesso: null,
    recording: false,
    voiceSupported: typeof webkitSpeechRecognition !== "undefined" || typeof SpeechRecognition !== "undefined",

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
