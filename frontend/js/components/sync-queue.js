/**
 * Componente de fila de sincronização.
 *
 * Exibe lista de itens pendentes/falhos na fila offline
 * com opção de retry manual e status visual.
 */
function syncQueueComponent() {
  return {
    items: [],
    loading: false,

    async loadQueue() {
      const database = await initDB();
      this.items = await database.syncQueue
        .where("status")
        .anyOf(["pending", "failed"])
        .toArray();
    },

    async retryAll() {
      this.loading = true;
      // Resetar falhos para pendente
      const database = await initDB();
      const failed = await database.syncQueue
        .where("status")
        .equals("failed")
        .toArray();

      for (const item of failed) {
        await database.syncQueue.update(item.id, { status: "pending" });
      }

      // Disparar sync
      await syncManager.syncAll();
      await this.loadQueue();
      this.loading = false;
    },

    getStatusColor(status) {
      if (status === "pending") return "text-yellow-400";
      if (status === "failed") return "text-red-400";
      return "text-green-400";
    },

    getStatusLabel(status) {
      if (status === "pending") return "Pendente";
      if (status === "failed") return "Falhou";
      return "Sincronizado";
    },
  };
}
