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

    // Abordagens com fotos vão pelo fluxo /abordagens/ (idempotente por client_id)
    // para obter o id do servidor e subir a mídia — o batch não retorna esse id (#5).
    const comFotos = pending.filter((p) => p.tipo === "abordagem" && p.fotos && p.fotos.length);
    const semFotos = pending.filter((p) => !(p.tipo === "abordagem" && p.fotos && p.fotos.length));

    try {
      let synced = 0;
      let failed = 0;

      for (const item of comFotos) {
        (await this._syncAbordagemComFotos(item)) ? synced++ : failed++;
      }

      if (semFotos.length > 0) {
        const items = semFotos.map((item) => ({
          client_id: item.clientId,
          tipo: item.tipo,
          dados: item.dados,
        }));

        const response = await api.post("/sync/batch", { items });

        for (const result of response.results) {
          const item = semFotos.find((p) => p.clientId === result.client_id);
          if (!item) continue;

          if (result.status === "ok") {
            await markSynced(item.id);
            synced++;
          } else {
            await markFailed(item.id, result.error || "Erro desconhecido");
            failed++;
          }
        }
      }

      this._notify("done", { synced, failed });
    } catch (err) {
      // Auth/rede: sync de background NUNCA deve causar logout — abortar silenciosamente
      if (err.status === 401 || err.status === 0) {
        this._notify("done", { synced: 0, failed: 0 });
        return;
      }
      // Se endpoint não existe ainda, sincronizar individualmente
      await this._syncIndividual(semFotos);
    } finally {
      this.syncing = false;
    }
  }

  async _syncAbordagemComFotos(item) {
    // Recria a abordagem pelo endpoint normal (dedup por client_id no payload)
    // e sobe cada foto persistida com o id retornado pelo servidor.
    try {
      const created = await api.post("/abordagens/", item.dados);
      for (const foto of item.fotos) {
        const extra = { tipo: foto.tipo, abordagem_id: created.id };
        if (foto.pessoa_id != null) extra.pessoa_id = foto.pessoa_id;
        if (foto.veiculo_id != null) extra.veiculo_id = foto.veiculo_id;
        await api.uploadFile("/fotos/upload", foto.blob, extra);
      }
      await markSynced(item.id);
      return true;
    } catch (err) {
      await markFailed(item.id, err.message || "Erro ao sincronizar abordagem com fotos");
      return false;
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
