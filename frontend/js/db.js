/**
 * Banco de dados local IndexedDB via Dexie.js.
 *
 * Gerencia fila de sincronização offline e cache local
 * de pessoas, veículos e passagens para autocomplete.
 */

// Importar Dexie via CDN (global script)
const DEXIE_CDN = "https://cdn.jsdelivr.net/npm/dexie@4/dist/dexie.min.js";

let db = null;

async function initDB() {
  if (db) return db;

  // Carregar Dexie se não estiver disponível
  if (typeof Dexie === "undefined") {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = DEXIE_CDN;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  db = new Dexie("argus");
  db.version(1).stores({
    syncQueue: "++id, tipo, status, criadoEm",
    pessoas: "id, nome, apelido",
    veiculos: "id, placa, modelo",
    passagens: "id, lei, artigo, nome_crime",
  });

  return db;
}

/**
 * Adiciona item à fila de sincronização offline.
 */
async function enqueueSync(tipo, dados) {
  const database = await initDB();
  return database.syncQueue.add({
    tipo,
    dados,
    status: "pending",
    criadoEm: new Date().toISOString(),
    tentativas: 0,
    clientId: crypto.randomUUID(),
  });
}

/**
 * Retorna todos os itens pendentes de sincronização.
 */
async function getPendingSync() {
  const database = await initDB();
  return database.syncQueue.where("status").equals("pending").toArray();
}

/**
 * Marca item como sincronizado.
 */
async function markSynced(id) {
  const database = await initDB();
  return database.syncQueue.update(id, { status: "synced" });
}

/**
 * Marca item como falha e incrementa tentativas.
 */
async function markFailed(id, erro) {
  const database = await initDB();
  const item = await database.syncQueue.get(id);
  return database.syncQueue.update(id, {
    status: "failed",
    erro,
    tentativas: (item?.tentativas || 0) + 1,
  });
}

/**
 * Conta itens pendentes na fila.
 */
async function countPending() {
  const database = await initDB();
  return database.syncQueue.where("status").equals("pending").count();
}

/**
 * Cache local de pessoas para autocomplete offline.
 */
async function cachePessoas(pessoas) {
  const database = await initDB();
  await database.pessoas.bulkPut(pessoas);
}

/**
 * Cache local de veículos para autocomplete offline.
 */
async function cacheVeiculos(veiculos) {
  const database = await initDB();
  await database.veiculos.bulkPut(veiculos);
}

/**
 * Busca pessoas no cache local.
 */
async function searchPessoasLocal(query) {
  const database = await initDB();
  const q = query.toLowerCase();
  return database.pessoas
    .filter((p) => p.nome.toLowerCase().includes(q) || (p.apelido && p.apelido.toLowerCase().includes(q)))
    .limit(10)
    .toArray();
}

/**
 * Busca veículos no cache local.
 */
async function searchVeiculosLocal(query) {
  const database = await initDB();
  const q = query.toUpperCase();
  return database.veiculos
    .filter((v) => v.placa.includes(q) || (v.modelo && v.modelo.toUpperCase().includes(q)))
    .limit(10)
    .toArray();
}
