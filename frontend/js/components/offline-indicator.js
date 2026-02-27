/**
 * Componente indicador de status offline.
 *
 * Badge visual que mostra estado de conectividade
 * e contagem de itens pendentes na fila de sync.
 */
function offlineIndicator() {
  return {
    online: navigator.onLine,
    pending: 0,

    init() {
      window.addEventListener("online", () => { this.online = true; });
      window.addEventListener("offline", () => { this.online = false; });

      // Atualizar contagem periodicamente
      setInterval(() => this.updateCount(), 5000);
      this.updateCount();
    },

    async updateCount() {
      this.pending = await countPending();
    },
  };
}
