/**
 * Componente de autocomplete genérico.
 *
 * Busca debounced na API (300ms) com fallback para cache
 * local (IndexedDB) quando offline. Suporta seleção múltipla.
 */
function autocompleteComponent(tipo) {
  return {
    query: "",
    results: [],
    selected: [],
    showDropdown: false,
    loading: false,
    _debounceTimer: null,

    onInput() {
      clearTimeout(this._debounceTimer);
      if (this.query.length < 2) {
        this.results = [];
        this.showDropdown = false;
        return;
      }
      this._debounceTimer = setTimeout(() => this.search(), 300);
    },

    async search() {
      this.loading = true;
      try {
        if (navigator.onLine) {
          if (tipo === "pessoa") {
            const data = await api.get(`/pessoas/?nome=${encodeURIComponent(this.query)}&limit=10`);
            this.results = data;
          } else if (tipo === "veiculo") {
            const data = await api.get(`/veiculos/?placa=${encodeURIComponent(this.query)}&limit=10`);
            this.results = data;
          }
        } else {
          // Fallback offline
          if (tipo === "pessoa") {
            this.results = await searchPessoasLocal(this.query);
          } else if (tipo === "veiculo") {
            this.results = await searchVeiculosLocal(this.query);
          }
        }
        this.showDropdown = this.results.length > 0;
      } catch {
        // Fallback offline em caso de erro
        if (tipo === "pessoa") {
          this.results = await searchPessoasLocal(this.query);
        } else {
          this.results = await searchVeiculosLocal(this.query);
        }
        this.showDropdown = this.results.length > 0;
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
    },

    remove(id) {
      this.selected = this.selected.filter((s) => s.id !== id);
    },

    getLabel(item) {
      if (tipo === "pessoa") {
        return item.apelido ? `${item.nome} (${item.apelido})` : item.nome;
      }
      if (tipo === "veiculo") {
        return item.modelo ? `${item.placa} — ${item.modelo}` : item.placa;
      }
      return item.nome || item.id;
    },

    getIds() {
      return this.selected.map((s) => s.id);
    },
  };
}
