/**
 * Banco de dados local IndexedDB via Dexie.js.
 *
 * Gerencia fila de sincronização offline e cache local
 * de pessoas, veículos e passagens para autocomplete.
 * Dados sensíveis são criptografados com AES-GCM via Web Crypto API.
 */

// Importar Dexie via CDN (global script)
const DEXIE_CDN = "https://cdn.jsdelivr.net/npm/dexie@4/dist/dexie.min.js";

let db = null;

// --- Crypto helpers (AES-256-GCM via Web Crypto API) ---
let _cryptoKey = null;

/**
 * Deriva chave AES-256 a partir de um segredo (ex: token JWT).
 * Usa PBKDF2 com salt fixo por dispositivo (armazenado em localStorage).
 */
async function initCryptoKey(secret) {
  if (_cryptoKey) return _cryptoKey;

  let salt = localStorage.getItem("argus_db_salt");
  if (!salt) {
    salt = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(16))));
    localStorage.setItem("argus_db_salt", salt);
  }

  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(secret), "PBKDF2", false, [
    "deriveKey",
  ]);

  _cryptoKey = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: enc.encode(salt), iterations: 100000, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
  return _cryptoKey;
}

/**
 * Criptografa string com AES-256-GCM. Retorna base64(iv + ciphertext).
 */
async function encryptField(plaintext) {
  if (!_cryptoKey || !plaintext) return plaintext;
  const enc = new TextEncoder();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, _cryptoKey, enc.encode(plaintext));
  const buf = new Uint8Array(iv.length + ct.byteLength);
  buf.set(iv);
  buf.set(new Uint8Array(ct), iv.length);
  return btoa(String.fromCharCode(...buf));
}

/**
 * Descriptografa string produzida por encryptField.
 */
async function decryptField(ciphertext) {
  if (!_cryptoKey || !ciphertext) return ciphertext;
  try {
    const buf = Uint8Array.from(atob(ciphertext), (c) => c.charCodeAt(0));
    const iv = buf.slice(0, 12);
    const ct = buf.slice(12);
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, _cryptoKey, ct);
    return new TextDecoder().decode(plain);
  } catch {
    return ciphertext; // dado não-criptografado (migração)
  }
}

/**
 * Criptografa campos sensíveis de um objeto pessoa.
 */
async function encryptPessoa(p) {
  return { ...p, nome: await encryptField(p.nome), apelido: await encryptField(p.apelido) };
}

/**
 * Descriptografa campos sensíveis de um objeto pessoa.
 */
async function decryptPessoa(p) {
  return { ...p, nome: await decryptField(p.nome), apelido: await decryptField(p.apelido) };
}

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
 * Campos sensíveis (nome, apelido) são criptografados com AES-GCM.
 */
async function cachePessoas(pessoas) {
  const database = await initDB();
  const encrypted = await Promise.all(pessoas.map(encryptPessoa));
  await database.pessoas.bulkPut(encrypted);
}

/**
 * Cache local de veículos para autocomplete offline.
 */
async function cacheVeiculos(veiculos) {
  const database = await initDB();
  await database.veiculos.bulkPut(veiculos);
}

/**
 * Busca pessoas no cache local (descriptografa antes de filtrar).
 */
async function searchPessoasLocal(query) {
  const database = await initDB();
  const q = query.toLowerCase();
  const all = await database.pessoas.toArray();
  const decrypted = await Promise.all(all.map(decryptPessoa));
  return decrypted
    .filter((p) => p.nome.toLowerCase().includes(q) || (p.apelido && p.apelido.toLowerCase().includes(q)))
    .slice(0, 10);
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
