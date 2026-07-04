/**
 * Componente autônomo de busca/cadastro/edição de veículo, usado como
 * modal na ficha do abordado.
 *
 * Não compartilha código com a tela de nova abordagem (frontend/js/pages/abordagem-nova.js) —
 * é um componente novo e isolado, escrito para ser plugado em pessoa-detalhe.js.
 *
 * Uso por quem consome o componente (ex.: pessoa-detalhe.js):
 *   x-data: "{ ...pessoaDetalhePage(id), ...veiculoFichaForm() }"
 *   Incluir no template: ${veiculoFichaFormHTML()}
 *
 *   Adicionar veículo à pessoa:
 *     this.pessoaIdParaVeiculo = pessoa.id;
 *     this.abrirModalAdicionarVeiculo();
 *
 *   Editar veículo já vinculado:
 *     this.abrirModalEditarVeiculo(v); // v no formato PessoaVeiculoRead
 *
 *   Após sucesso (criação+vínculo, edição ou vínculo direto via busca), o
 *   componente dispara o evento customizado "veiculo-vinculado" via
 *   window.dispatchEvent(new CustomEvent(...)). Quem consome deve escutar
 *   com @veiculo-vinculado.window="recarregarVeiculos()" (ou similar) para
 *   atualizar sua própria lista — este componente não sabe como fazer isso.
 *   (Nota: usa window.dispatchEvent em vez de this.$dispatch porque o modo
 *   "buscar" chama confirmarVeiculo() depois de já remover do DOM o botão
 *   que originou o clique — this.$dispatch ficaria ancorado a um elemento
 *   desconectado, sem pai para o evento borbulhar até window.)
 */

/**
 * Retorna o HTML do modal de busca/cadastro/edição de veículo.
 * Usa "modalVeiculo"/"modoVeiculo"/"veiculoForm" (não nomes genéricos)
 * para evitar conflito com o estado da página host.
 * @returns {string} HTML do modal.
 */
function veiculoFichaFormHTML() {
  return `
    <div x-show="modalVeiculo" x-cloak
         @click.self="fecharModalVeiculo()"
         style="position: fixed; top: var(--header-height); left: 0; right: 0; bottom: var(--bottom-nav-height); background: rgba(5,10,15,0.7); z-index: 55; display: flex; align-items: center; justify-content: center; padding: 1rem;">
      <div class="glass-card"
           style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 26rem; max-height: 100%; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; box-sizing: border-box;"
           @click.stop>

        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;">
            <span x-show="modoVeiculo === 'buscar'">Adicionar Veículo</span>
            <span x-show="modoVeiculo === 'novo'">Cadastrar Veículo</span>
            <span x-show="modoVeiculo === 'editar'">Editar Veículo</span>
          </h3>
          <button @click="fecharModalVeiculo()" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
        </div>

        <!-- Modo buscar -->
        <div x-show="modoVeiculo === 'buscar'" style="display: flex; flex-direction: column; gap: 0.5rem;">
          <div>
            <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Buscar por placa</label>
            <input type="text" :value="buscaPlaca"
                   @input="buscaPlaca = formatarPlaca($event.target.value); onBuscaPlacaInput()"
                   placeholder="ABC-1234" maxlength="8"
                   style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-data); text-transform: uppercase; box-sizing: border-box;"
                   class="foc-input-primary">
          </div>

          <div x-show="buscando" style="display: flex; justify-content: center; padding: 0.5rem 0;">
            <span class="spinner"></span>
          </div>

          <!-- Resultados -->
          <div x-show="!buscando && resultadosBusca.length > 0" style="display: flex; flex-direction: column; border: 1px solid var(--color-border); border-radius: 4px; overflow: hidden;">
            <template x-for="v in resultadosBusca" :key="v.id">
              <button type="button" @click="selecionarVeiculoExistente(v)"
                      :disabled="salvandoVeiculo"
                      class="hov-row-surface"
                      style="width: 100%; text-align: left; padding: 0.5rem 0.75rem; background: transparent; border: none; border-bottom: 1px solid var(--color-border); cursor: pointer; display: flex; flex-direction: column; gap: 0.125rem;">
                <span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.05em;" x-text="formatarPlaca(v.placa || '')"></span>
                <span x-show="v.modelo || v.cor || v.ano"
                      style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted);"
                      x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></span>
              </button>
            </template>
          </div>

          <!-- Sem resultados -->
          <p x-show="!buscando && buscaPlaca.trim().length >= 2 && resultadosBusca.length === 0"
             style="font-family: var(--font-data); font-size: 0.8rem; color: var(--color-text-dim); margin: 0;">
            Nenhum veículo encontrado.
          </p>

          <button type="button" @click="irParaCadastroNovo()"
                  style="align-self: flex-start; background: none; border: none; cursor: pointer; color: var(--color-primary); font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.25rem 0;">
            + Cadastrar veículo novo
          </button>

          <p x-show="erroVeiculo" style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-danger); margin: 0;" x-text="erroVeiculo"></p>
        </div>

        <!-- Modo novo / editar (mesmo formulário) -->
        <div x-show="modoVeiculo === 'novo' || modoVeiculo === 'editar'" style="display: flex; flex-direction: column; gap: 0.5rem;">
          <div>
            <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
              Placa <span x-show="modoVeiculo === 'novo'" style="color: var(--color-danger)">*</span>
            </label>
            <input type="text" :value="veiculoForm.placa"
                   @input="veiculoForm.placa = formatarPlaca($event.target.value)"
                   :disabled="modoVeiculo === 'editar'"
                   placeholder="ABC-1234" maxlength="8"
                   style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-data); text-transform: uppercase; box-sizing: border-box;"
                   :style="modoVeiculo === 'editar' ? 'opacity: 0.6; cursor: not-allowed;' : ''"
                   class="foc-input-primary">
          </div>
          <div>
            <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Modelo</label>
            <input type="text" x-model="veiculoForm.modelo" placeholder="Ex: Gol"
                   style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                   class="foc-input-primary input-upper">
          </div>
          <div>
            <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Cor</label>
            <select x-model="corDropdown" @change="onCorChange()"
                    style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                    class="foc-input-primary">
              <option value="">Selecione...</option>
              <template x-for="c in (window.CORES_VEICULO || [])" :key="c"><option :value="c" x-text="c"></option></template>
              <option value="__outra__">Outra...</option>
            </select>
            <input x-show="corDropdown === '__outra__'" type="text" x-model="veiculoForm.cor" placeholder="Digite a cor"
                   style="width: 100%; margin-top: 0.5rem; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                   class="foc-input-primary input-upper">
          </div>
          <div>
            <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Ano</label>
            <input type="number" x-model.number="veiculoForm.ano" placeholder="2020" min="1900" max="2100"
                   style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                   class="foc-input-primary">
          </div>

          <p x-show="erroVeiculo" style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-danger); margin: 0;" x-text="erroVeiculo"></p>

          <div style="display: flex; gap: 0.5rem; padding-top: 0.25rem;">
            <button type="button" @click="modoVeiculo === 'novo' ? abrirModalAdicionarVeiculo() : fecharModalVeiculo()"
                    style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">
              <span x-text="modoVeiculo === 'novo' ? 'Voltar' : 'Cancelar'"></span>
            </button>
            <button type="button" @click="confirmarVeiculo()"
                    :disabled="salvandoVeiculo || (modoVeiculo === 'novo' && !veiculoForm.placa.trim())"
                    class="btn btn-primary"
                    style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">
              <span x-show="!salvandoVeiculo">Salvar</span>
              <span x-show="salvandoVeiculo" class="spinner"></span>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Componente Alpine.js de busca/cadastro/edição de veículo (modal).
 *
 * Três modos: "buscar" (busca por placa + vínculo direto), "novo"
 * (cadastro de veículo novo) e "editar" (edição de veículo já vinculado
 * à pessoa). Não conhece a página que o consome — comunica conclusão via
 * evento customizado "veiculo-vinculado" (window.dispatchEvent).
 *
 * @returns {object} Estado e métodos do componente Alpine.
 */
function veiculoFichaForm() {
  return {
    modalVeiculo: false,
    modoVeiculo: "buscar", // 'buscar' | 'novo' | 'editar'
    buscaPlaca: "",
    resultadosBusca: [],
    buscando: false,
    veiculoForm: { id: null, placa: "", modelo: "", cor: "", ano: null },
    corDropdown: "",
    salvandoVeiculo: false,
    erroVeiculo: "",
    _buscaTimer: null,
    // Setado por quem consome o componente antes de abrir o modal de
    // adicionar (ex.: this.pessoaIdParaVeiculo = pessoa.id). Usado para
    // vincular o veículo criado/selecionado à pessoa em questão.
    pessoaIdParaVeiculo: null,

    /**
     * Abre o modal no modo "buscar", pronto para adicionar um veículo à
     * pessoa já indicada em pessoaIdParaVeiculo (setado pelo consumidor
     * antes desta chamada).
     */
    abrirModalAdicionarVeiculo() {
      this.modoVeiculo = "buscar";
      this.buscaPlaca = "";
      this.resultadosBusca = [];
      this.buscando = false;
      this.veiculoForm = { id: null, placa: "", modelo: "", cor: "", ano: null };
      this.corDropdown = "";
      this.erroVeiculo = "";
      this.salvandoVeiculo = false;
      clearTimeout(this._buscaTimer);
      this.modalVeiculo = true;
    },

    /**
     * Abre o modal no modo "editar" para um veículo já vinculado à pessoa.
     * @param {object} v - Veículo no formato PessoaVeiculoRead
     *   ({veiculo_id, placa, modelo, cor, ano, ...}).
     */
    abrirModalEditarVeiculo(v) {
      this.modoVeiculo = "editar";
      this.buscaPlaca = "";
      this.resultadosBusca = [];
      this.buscando = false;
      this.erroVeiculo = "";
      this.salvandoVeiculo = false;
      this.veiculoForm = {
        id: v.veiculo_id,
        // Placa fica em disabled neste modo (nunca é reenviada ao backend) —
        // formatarPlaca() aqui é só cosmético, para exibir "ABC-1234" em vez
        // do valor cru normalizado ("ABC1234") vindo da API.
        placa: formatarPlaca(v.placa || ""),
        modelo: v.modelo || "",
        cor: v.cor || "",
        ano: v.ano ?? null,
      };
      this.corDropdown = this._corParaDropdown(this.veiculoForm.cor);
      // Modo editar não vincula — não depende de pessoaIdParaVeiculo.
      this.pessoaIdParaVeiculo = null;
      clearTimeout(this._buscaTimer);
      this.modalVeiculo = true;
    },

    /** Fecha o modal e cancela busca pendente. */
    fecharModalVeiculo() {
      this.modalVeiculo = false;
      clearTimeout(this._buscaTimer);
    },

    /**
     * Handler do input de busca por placa: debounce de 300ms antes de
     * consultar GET /veiculos/?placa=.
     */
    onBuscaPlacaInput() {
      clearTimeout(this._buscaTimer);
      this.erroVeiculo = "";
      if (this.buscaPlaca.trim().length < 2) {
        this.resultadosBusca = [];
        this.buscando = false;
        return;
      }
      this._buscaTimer = setTimeout(() => this._buscarVeiculos(), 300);
    },

    /** Consulta a API por veículos cuja placa contém o texto buscado. */
    async _buscarVeiculos() {
      this.buscando = true;
      try {
        const data = await api.get(`/veiculos/?placa=${encodeURIComponent(this.buscaPlaca.trim())}&limit=5`);
        this.resultadosBusca = data || [];
      } catch (err) {
        this.erroVeiculo = err?.message || "Erro ao buscar veículos.";
        this.resultadosBusca = [];
      } finally {
        this.buscando = false;
      }
    },

    /**
     * Seleciona um veículo encontrado na busca e já confirma o vínculo
     * direto com a pessoa (sem reabrir formulário).
     * @param {object} v - Veículo retornado por GET /veiculos/ (VeiculoRead).
     */
    selecionarVeiculoExistente(v) {
      this.veiculoForm = {
        id: v.id,
        placa: v.placa || "",
        modelo: v.modelo || "",
        cor: v.cor || "",
        ano: v.ano ?? null,
      };
      this.resultadosBusca = [];
      this.confirmarVeiculo();
    },

    /** Vai para o modo "novo", pré-preenchendo a placa com o que foi digitado na busca. */
    irParaCadastroNovo() {
      this.erroVeiculo = "";
      this.veiculoForm = { id: null, placa: this.buscaPlaca || "", modelo: "", cor: "", ano: null };
      this.corDropdown = "";
      this.modoVeiculo = "novo";
    },

    /** "Outra..." libera campo de texto livre; demais opções definem a cor direto. */
    onCorChange() {
      this.veiculoForm.cor = this.corDropdown === "__outra__" ? "" : this.corDropdown;
    },

    /**
     * Mapeia uma cor já salva para o valor do dropdown: usa a própria cor
     * se estiver na lista fixa, senão cai em "Outra..." mantendo o texto.
     * @param {string} cor - Cor salva no veículo.
     * @returns {string} Valor a usar em corDropdown.
     */
    _corParaDropdown(cor) {
      if (!cor) return "";
      const lista = window.CORES_VEICULO || [];
      return lista.includes(cor) ? cor : "__outra__";
    },

    /**
     * Salva conforme o modo atual (cria, edita ou vincula veículo já
     * existente), fecha o modal e avisa quem consome via evento
     * "veiculo-vinculado".
     */
    async confirmarVeiculo() {
      this.erroVeiculo = "";
      if (this.modoVeiculo === "novo" && !this.veiculoForm.placa.trim()) {
        this.erroVeiculo = "Placa é obrigatória.";
        return;
      }

      this.salvandoVeiculo = true;
      try {
        if (this.modoVeiculo === "editar") {
          await this._salvarEdicao();
        } else if (this.modoVeiculo === "novo") {
          await this._salvarNovo();
        } else {
          await this._vincularExistente();
        }
        this.fecharModalVeiculo();
        // Dispara direto em window (em vez de this.$dispatch): o modo "buscar"
        // chega aqui via selecionarVeiculoExistente(), que já removeu o botão
        // clicado do DOM (resultadosBusca = []) antes deste await terminar —
        // this.$dispatch ficaria ancorado a um elemento desconectado, cujo
        // dispatchEvent não tem mais pai para borbulhar até window.
        window.dispatchEvent(new CustomEvent("veiculo-vinculado"));
      } catch (err) {
        this.erroVeiculo = err?.message || "Erro ao salvar veículo.";
      } finally {
        this.salvandoVeiculo = false;
      }
    },

    /** Cria o veículo e, se houver pessoa alvo, vincula-o em seguida. */
    async _salvarNovo() {
      const data = { placa: this.veiculoForm.placa.trim() };
      if (this.veiculoForm.modelo?.trim()) data.modelo = this.veiculoForm.modelo.trim();
      if (this.veiculoForm.cor?.trim()) data.cor = this.veiculoForm.cor.trim();
      if (this.veiculoForm.ano) data.ano = this.veiculoForm.ano;

      const veiculo = await api.post("/veiculos/", data);
      if (this.pessoaIdParaVeiculo) {
        await api.post(`/pessoas/${this.pessoaIdParaVeiculo}/veiculos/${veiculo.id}`);
      }
    },

    /** Atualiza modelo/cor/ano do veículo (placa é imutável). */
    async _salvarEdicao() {
      const data = {};
      if (this.veiculoForm.modelo?.trim()) data.modelo = this.veiculoForm.modelo.trim();
      if (this.veiculoForm.cor?.trim()) data.cor = this.veiculoForm.cor.trim();
      if (this.veiculoForm.ano) data.ano = this.veiculoForm.ano;
      await api.put(`/veiculos/${this.veiculoForm.id}`, data);
    },

    /** Vincula um veículo já existente (selecionado na busca) à pessoa alvo. */
    async _vincularExistente() {
      if (!this.pessoaIdParaVeiculo) {
        throw new Error("Nenhuma pessoa definida para vincular o veículo.");
      }
      await api.post(`/pessoas/${this.pessoaIdParaVeiculo}/veiculos/${this.veiculoForm.id}`);
    },
  };
}
