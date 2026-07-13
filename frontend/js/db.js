/**
 * Banco de dados local IndexedDB via Dexie.js.
 *
 * Gerencia fila de sincronização offline e cache local
 * de pessoas, veículos e passagens para autocomplete.
 * Dados sensíveis são criptografados com AES-GCM via Web Crypto API.
 */

// Dexie self-hosted (same-origin) — carregado sob demanda; precacheado pelo SW
// para funcionar offline (ver frontend/vendor/ e sw.js).
const DEXIE_CDN = "/vendor/dexie.min.js";

// Máximo de tentativas de sincronização antes de "estacionar" um item failed.
// Itens failed abaixo deste limite são reprocessados automaticamente; acima,
// ficam parados aguardando atenção manual (evita retry infinito de erro
// permanente, ex.: validação).
const MAX_SYNC_ATTEMPTS = 5;

let db = null;

// Cache em memória das pessoas já descriptografadas, para não re-decriptar todo
// o cache local a cada tecla na busca (G3-5). Invalidado ao recachear pessoas
// (cachePessoas) ou no logout (clearLocalDB).
let _pessoasDecryptCache = null;

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
 * Garante que a chave de criptografia do IndexedDB está ativa.
 *
 * Sem isto, _cryptoKey ficava null e encryptField/decryptField devolviam
 * texto puro — PII em claro no IndexedDB. Deriva a chave de um segredo
 * aleatório por instalação (argus_db_secret em localStorage), gerado no
 * primeiro login e apagado no logout (ver clearLocalDB). Sobrevive a F5.
 */
async function ensureCryptoReady() {
  let secret = localStorage.getItem("argus_db_secret");
  if (!secret) {
    secret = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))));
    localStorage.setItem("argus_db_secret", secret);
  }
  return initCryptoKey(secret);
}

/**
 * Apaga todos os dados locais sensíveis (logout em dispositivo compartilhado).
 *
 * Remove o banco IndexedDB (PII de pessoas + fila offline) e o segredo/salt
 * de criptografia. O Cache Storage do Service Worker é limpo separadamente
 * em auth.logout(). Best-effort: nunca lança.
 */
async function clearLocalDB() {
  _cryptoKey = null;
  _pessoasDecryptCache = null;
  try {
    if (db) {
      db.close();
      db = null;
    }
    if (typeof Dexie !== "undefined") {
      await Dexie.delete("argus");
    } else if (self.indexedDB) {
      indexedDB.deleteDatabase("argus");
    }
  } catch {
    /* best-effort */
  }
  localStorage.removeItem("argus_db_secret");
  localStorage.removeItem("argus_db_salt");
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
      script.onerror = () => reject(new Error("Falha ao carregar Dexie: CDN indisponível"));
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
async function enqueueSync(tipo, dados, fotos = []) {
  const database = await initDB();
  // `fotos` (Blob/File) é persistido nativamente pelo IndexedDB para que a
  // mídia não se perca ao sincronizar uma abordagem criada offline (#5 auditoria).
  return database.syncQueue.add({
    tipo,
    // PII do payload (nomes, observação, GPS, pessoas, veículos) cifrada
    // at-rest no IndexedDB; decriptada em getPendingSync antes do envio (G3-2).
    dados: await encryptField(JSON.stringify(dados)),
    fotos,
    status: "pending",
    criadoEm: new Date().toISOString(),
    tentativas: 0,
    clientId: crypto.randomUUID(),
    // Guarnição da sessão no momento do registro offline — usada em
    // getPendingSync para detectar troca de equipe antes de sincronizar
    // (achado #18/2026-07-13). null se indisponível (ex.: perfil incompleto).
    guarnicaoId: typeof auth !== "undefined" && auth.user ? auth.user.guarnicao_id : null,
  });
}

/**
 * Limpa a fila local de sincronização quando a guarnição do usuário muda.
 *
 * Itens enfileirados offline sob a guarnição anterior não podem ser
 * sincronizados com segurança sob a sessão atual — sincronizá-los atribuiria
 * o registro de campo à equipe nova, um vazamento entre tenants (achado
 * #18/2026-07-13). Best-effort: nunca lança.
 */
async function purgeSyncQueueOnTeamChange() {
  try {
    const database = await initDB();
    await database.syncQueue.clear();
  } catch {
    /* best-effort */
  }
}

/**
 * Decripta o payload `dados` de um item da fila para o objeto original.
 *
 * Tolerante a migração: itens antigos gravados como objeto em claro (antes do
 * G3-2) ou como JSON em claro são devolvidos sem erro. Defensivo: se não for
 * JSON após o decrypt, devolve o valor cru.
 */
async function _decryptDados(raw) {
  if (raw == null || typeof raw !== "string") return raw; // legado: objeto
  const plano = await decryptField(raw);
  try {
    return JSON.parse(plano);
  } catch {
    return raw;
  }
}

/**
 * Predicado de item sincronizável: pendente ou falho ainda dentro do limite
 * de tentativas (reprocessamento automático de falhas transitórias).
 */
function _sincronizavel(item) {
  return (
    item.status === "pending" ||
    (item.status === "failed" && (item.tentativas || 0) < MAX_SYNC_ATTEMPTS)
  );
}

/**
 * Retorna os itens a sincronizar: pendentes + falhos reprocessáveis.
 *
 * Itens marcados como `failed` por erro transitório (rede/5xx) voltam a ser
 * tentados até MAX_SYNC_ATTEMPTS, evitando a perda silenciosa de dados de
 * campo que ficavam presos em `failed` para sempre.
 *
 * Itens enfileirados sob uma guarnição diferente da sessão atual (equipe do
 * operador trocada após o registro offline, antes da fila sincronizar) são
 * quarentenados em vez de liberados — sincronizá-los agora atribuiria o
 * registro à equipe errada (achado #18/2026-07-13). Ficam em `failed` e
 * "estacionam" após MAX_SYNC_ATTEMPTS como qualquer outra falha permanente.
 */
async function getPendingSync() {
  const database = await initDB();
  const items = await database.syncQueue.filter(_sincronizavel).toArray();
  // Garante a chave antes de decriptar (evita falso failed se o sync disparar
  // antes do ensureCryptoReady do boot). Só quando há itens e segredo presente.
  if (items.length && localStorage.getItem("argus_db_secret")) {
    await ensureCryptoReady();
  }
  const guarnicaoAtual = typeof auth !== "undefined" && auth.user ? auth.user.guarnicao_id : null;
  const liberados = [];
  for (const item of items) {
    if (
      item.guarnicaoId != null &&
      guarnicaoAtual != null &&
      item.guarnicaoId !== guarnicaoAtual
    ) {
      await markFailed(item.id, "Item pertence a outra equipe — sincronização bloqueada");
      continue;
    }
    item.dados = await _decryptDados(item.dados);
    liberados.push(item);
  }
  return liberados;
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
 * Conta itens na fila ainda por sincronizar (pendentes + falhos reprocessáveis).
 */
async function countPending() {
  const database = await initDB();
  return database.syncQueue.filter(_sincronizavel).count();
}

/**
 * Cache local de pessoas para autocomplete offline.
 * Campos sensíveis (nome, apelido) são criptografados com AES-GCM.
 */
async function cachePessoas(pessoas) {
  const database = await initDB();
  const encrypted = await Promise.all(pessoas.map(encryptPessoa));
  await database.pessoas.bulkPut(encrypted);
  _pessoasDecryptCache = null; // invalida o cache decriptado (dados mudaram)
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
  // Decripta o cache uma vez e reutiliza nas buscas seguintes (memoização);
  // antes, cada tecla re-decriptava todos os registros (G3-5).
  if (_pessoasDecryptCache === null) {
    const all = await database.pessoas.toArray();
    _pessoasDecryptCache = await Promise.all(all.map(decryptPessoa));
  }
  return _pessoasDecryptCache
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
