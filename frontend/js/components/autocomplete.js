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

    _isCPF(value) {
      return /^\d{3,}[\d.\-]*$/.test(value.trim());
    },

    _filtrarLocalmente() {
      const q = this.query.toLowerCase();
      if (tipo === "pessoa") {
        return this._allResults.filter(item =>
          (item.nome || "").toLowerCase().includes(q) ||
          (item.apelido || "").toLowerCase().includes(q) ||
          (item.cpf_masked || "").includes(q)
        );
      }
      if (tipo === "veiculo") {
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
      if (this.query.length < 2) {
        this.results = [];
        this._allResults = [];
        this.showDropdown = false;
        return;
      }
      // Filtro local imediato nos resultados já carregados
      if (this._allResults.length > 0) {
        this.results = this._filtrarLocalmente();
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
        this.results = this._filtrarLocalmente();
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
