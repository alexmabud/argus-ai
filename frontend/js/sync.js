/**
 * Gerenciador de sincronização offline → online.
 *
 * Monitora conectividade, processa fila de itens pendentes
 * e sincroniza batch com backend via /api/v1/sync/batch.
 */
class SyncManager {
  constructor() {
    this.syncing = false;
    this.intervalId = null;
    this.onStatusChange = null;
  }

  start() {
    // Escutar eventos de conectividade
    window.addEventListener("online", () => this.syncAll());

    // Escutar mensagem do Service Worker
    navigator.serviceWorker?.addEventListener("message", (event) => {
      if (event.data?.type === "SYNC_NOW") this.syncAll();
    });

    // Poll a cada 30 segundos
    this.intervalId = setInterval(() => {
      if (navigator.onLine && !this.syncing) this.syncAll();
    }, 30000);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  async syncAll() {
    if (this.syncing || !navigator.onLine) return;

    const pending = await getPendingSync();
    if (pending.length === 0) return;

    this.syncing = true;
    this._notify("syncing", { total: pending.length });

    try {
      const items = pending.map((item) => ({
        client_id: item.clientId,
        tipo: item.tipo,
        dados: item.dados,
      }));

      const response = await api.post("/sync/batch", { items });

      let synced = 0;
      let failed = 0;

      for (const result of response.results) {
        const item = pending.find((p) => p.clientId === result.client_id);
        if (!item) continue;

        if (result.status === "ok") {
          await markSynced(item.id);
          synced++;
        } else {
          await markFailed(item.id, result.error || "Erro desconhecido");
          failed++;
        }
      }

      this._notify("done", { synced, failed });
    } catch (err) {
      // Se endpoint não existe ainda, sincronizar individualmente
      await this._syncIndividual(pending);
    } finally {
      this.syncing = false;
    }
  }

  async _syncIndividual(pending) {
    let synced = 0;
    let failed = 0;

    for (const item of pending) {
      try {
        const endpointMap = {
          abordagem: "/abordagens/",
          pessoa: "/pessoas/",
          veiculo: "/veiculos/",
        };
        const endpoint = endpointMap[item.tipo];
        if (!endpoint) {
          await markFailed(item.id, `Tipo desconhecido: ${item.tipo}`);
          failed++;
          continue;
        }
        await api.post(endpoint, item.dados);
        await markSynced(item.id);
        synced++;
      } catch (err) {
        await markFailed(item.id, err.message || "Erro na sincronização");
        failed++;
      }
    }

    this._notify("done", { synced, failed });
  }

  _notify(status, detail = {}) {
    if (this.onStatusChange) {
      this.onStatusChange(status, detail);
    }
  }
}

// Singleton global
const syncManager = new SyncManager();
