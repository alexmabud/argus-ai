/**
 * Componente de autocomplete genérico.
 *
 * Busca debounced na API (300ms) com fallback para cache
 * local (IndexedDB) quando offline. Suporta seleção múltipla.
 * Para tipo "pessoa", detecta CPF automaticamente e exibe
 * opção de cadastro quando não encontra resultados.
 */
function autocompleteComponent(tipo) {
  return {
    query: "",
    results: [],
    _allResults: [],
    selected: [],
    showDropdown: false,
    loading: false,
    noResults: false,
    _debounceTimer: null,
    cpfErro: "",

    _isCPF(value) {
      return /^\d{3,}[\d.\-]*$/.test(value.trim());
    },

    _normalizar(s) {
      return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    },

    _tokensOrdenados(haystack, tokens) {
      let pos = 0;
      for (const t of tokens) {
        const idx = haystack.indexOf(t, pos);
        if (idx === -1) return false;
        pos = idx + t.length;
      }
      return true;
    },

    _filtrarLocalmente() {
      if (tipo === "pessoa") {
        const tokens = this._normalizar(this.query).split(/\s+/).filter(t => t);
        return this._allResults.filter(item => {
          if ((item.cpf_masked || "").includes(this.query)) return true;
          const nome = this._normalizar(item.nome);
          const apelido = this._normalizar(item.apelido);
          return this._tokensOrdenados(nome, tokens) || this._tokensOrdenados(apelido, tokens);
        });
      }
      if (tipo === "veiculo") {
        const q = this.query.toLowerCase();
        return this._allResults.filter(item =>
          (item.placa || "").toLowerCase().includes(q) ||
          (item.modelo || "").toLowerCase().includes(q)
        );
      }
      return this._allResults;
    },

    onInput() {
      clearTimeout(this._debounceTimer);
      this.noResults = false;

      if (tipo === "pessoa" && this._isCPF(this.query)) {
        const digits = this.query.replace(/\D/g, "");
        if (digits.length === 11 && !validarCPF(this.query)) {
          this.cpfErro = "CPF inválido";
          this.results = [];
          this._allResults = [];
          this.showDropdown = false;
          return;
        }
      }
      this.cpfErro = "";

      if (this.query.length < 2) {
        this.results = [];
        this._allResults = [];
        this.showDropdown = false;
        return;
      }
      // Filtro local imediato nos resultados já carregados
      // Busca por CPF não usa filtro local: cpf_masked é mascarado (LGPD) e não contém o CPF completo
      if (this._allResults.length > 0) {
        const isCpfSearch = tipo === "pessoa" && this._isCPF(this.query);
        this.results = isCpfSearch ? this._allResults : this._filtrarLocalmente();
        this.showDropdown = this.results.length > 0;
      }
      this._debounceTimer = setTimeout(() => this.search(), 300);
    },

    async search() {
      this.loading = true;
      this.noResults = false;
      try {
        let data;
        if (navigator.onLine) {
          if (tipo === "pessoa") {
            const param = this._isCPF(this.query) ? "cpf" : "nome";
            data = await api.get(`/pessoas/?${param}=${encodeURIComponent(this.query)}&limit=10`);
          } else if (tipo === "veiculo") {
            data = await api.get(`/veiculos/?placa=${encodeURIComponent(this.query)}&limit=10`);
          }
        } else {
          // Fallback offline
          if (tipo === "pessoa") {
            data = await searchPessoasLocal(this.query);
          } else if (tipo === "veiculo") {
            data = await searchVeiculosLocal(this.query);
          }
        }
        this._allResults = data || [];
        // Busca por CPF não usa filtro local: cpf_masked é mascarado (LGPD) e não contém o CPF completo
        const isCpfSearch = tipo === "pessoa" && this._isCPF(this.query);
        this.results = isCpfSearch ? this._allResults : this._filtrarLocalmente();
        this.noResults = this.results.length === 0 && this.query.length >= 2;
        this.showDropdown = this.results.length > 0 || this.noResults;
      } catch {
        // Fallback offline em caso de erro
        let data;
        if (tipo === "pessoa") {
          data = await searchPessoasLocal(this.query);
        } else {
          data = await searchVeiculosLocal(this.query);
        }
        this._allResults = data || [];
        this.results = this._filtrarLocalmente();
        this.noResults = this.results.length === 0 && this.query.length >= 2;
        this.showDropdown = this.results.length > 0 || this.noResults;
      } finally {
        this.loading = false;
      }
    },

    select(item) {
      if (!this.selected.find((s) => s.id === item.id)) {
        this.selected.push(item);
      }
      this.query = "";
      this.results = [];
      this.showDropdown = false;
      this.noResults = false;
    },

    remove(id) {
      this.selected = this.selected.filter((s) => s.id !== id);
    },

    getLabel(item) {
      if (tipo === "pessoa") {
        return item.apelido ? `${item.nome} (${item.apelido})` : item.nome;
      }
      if (tipo === "veiculo") {
        const placa = formatarPlaca(item.placa || "");
        return item.modelo ? `${placa} — ${item.modelo}` : placa;
      }
      return item.nome || item.id;
    },

    getIds() {
      return this.selected.map((s) => s.id);
    },
  };
}
