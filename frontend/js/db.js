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

// Idem para veículos (achado #19/2026-07-13) — mesmo padrão de memoização.
let _veiculosDecryptCache = null;

// --- Crypto helpers (AES-256-GCM via Web Crypto API) ---
let _cryptoKey = null;

/**
 * Garante que a chave de criptografia do IndexedDB está ativa.
 *
 * A chave AES-256-GCM é gerada não-extraível (extractable=false) e
 * persistida como CryptoKey nativo em um object store dedicado do próprio
 * IndexedDB — nunca como bytes em localStorage. Antes, a chave era derivada
 * (PBKDF2) de um segredo salvo em localStorage: qualquer XSS conseguia ler
 * esse segredo em claro e decifrar todo o cache local offline, derrotando o
 * propósito da cifra at-rest (achado #19/2026-07-13). Uma chave não-extraível
 * pode ser usada para encrypt/decrypt via crypto.subtle, mas seus bytes brutos
 * nunca podem ser exportados — nem por um script injetado na própria página.
 */
async function ensureCryptoReady() {
  if (_cryptoKey) return _cryptoKey;

  const database = await initDB();
  const stored = await database.cryptoKeys.get("indexeddb-key");
  if (stored) {
    _cryptoKey = stored.key;
    return _cryptoKey;
  }

  _cryptoKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, [
    "encrypt",
    "decrypt",
  ]);
  await database.cryptoKeys.put({ id: "indexeddb-key", key: _cryptoKey });

  // Migração do esquema antigo (PBKDF2 + segredo em localStorage): qualquer
  // cache de pessoas/veículos cifrado com a chave anterior fica ilegível sob
  // a chave nova — descarta em vez de exibir ciphertext bruto na
  // autocomplete até o próximo recache online. Tabelas vazias em instalação
  // nova tornam isto um no-op inofensivo.
  await database.pessoas.clear().catch(() => {});
  await database.veiculos.clear().catch(() => {});
  _pessoasDecryptCache = null;
  _veiculosDecryptCache = null;
  localStorage.removeItem("argus_db_secret");
  localStorage.removeItem("argus_db_salt");

  return _cryptoKey;
}

/**
 * Apaga todos os dados locais sensíveis (logout em dispositivo compartilhado).
 *
 * Remove o banco IndexedDB inteiro (PII de pessoas/veículos, fila offline e
 * a chave de criptografia não-extraível). O Cache Storage do Service Worker
 * é limpo separadamente em auth.logout(). Best-effort: nunca lança.
 */
async function clearLocalDB() {
  _cryptoKey = null;
  _pessoasDecryptCache = null;
  _veiculosDecryptCache = null;
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
  // Resíduo do esquema anterior (pré-#19) — limpeza defensiva.
  localStorage.removeItem("argus_db_secret");
  localStorage.removeItem("argus_db_salt");
}

/**
 * Criptografa string com AES-256-GCM. Retorna base64(iv + ciphertext).
 *
 * Lança se a chave ainda não estiver pronta, em vez de devolver o texto
 * puro em silêncio — antes, uma chave ausente fazia PII ser gravada sem
 * cifra no IndexedDB sem nenhum sinal de erro (achado #19/2026-07-13).
 * Chamadores que persistem dado sensível devem aguardar ensureCryptoReady()
 * antes (todos os pontos de escrita deste módulo já fazem isso).
 */
async function encryptField(plaintext) {
  if (!plaintext) return plaintext;
  if (!_cryptoKey) {
    throw new Error("Chave de criptografia local indisponível — chame ensureCryptoReady() antes");
  }
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

/**
 * Criptografa campos sensíveis de um objeto veículo (achado #19/2026-07-13).
 *
 * Placa identifica o veículo (e indiretamente o motorista/local); mesmo
 * tratamento de nome/apelido de pessoa.
 */
async function encryptVeiculo(v) {
  return {
    ...v,
    placa: await encryptField(v.placa),
    modelo: await encryptField(v.modelo),
    cor: await encryptField(v.cor),
  };
}

/**
 * Descriptografa campos sensíveis de um objeto veículo.
 */
async function decryptVeiculo(v) {
  return {
    ...v,
    placa: await decryptField(v.placa),
    modelo: await decryptField(v.modelo),
    cor: await decryptField(v.cor),
  };
}

/**
 * Criptografa um Blob (foto) com AES-256-GCM.
 *
 * Retorna um envelope serializável pelo IndexedDB (ArrayBuffer cifrado +
 * IV + content-type), nunca o Blob em claro — fotos na fila offline
 * ficavam persistidas sem cifra (achado #19/2026-07-13).
 */
async function encryptBlob(blob) {
  if (!_cryptoKey) {
    throw new Error("Chave de criptografia local indisponível — chame ensureCryptoReady() antes");
  }
  const buf = await blob.arrayBuffer();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, _cryptoKey, buf);
  return { _cifrado: true, iv: Array.from(iv), ciphertext, type: blob.type };
}

/**
 * Descriptografa um envelope produzido por encryptBlob() de volta a um Blob.
 *
 * Tolerante a itens legados da fila gravados antes da cifra de fotos
 * (Blob puro, não-envelope) — devolvidos como estão.
 */
async function decryptBlob(envelope) {
  if (!envelope || !envelope._cifrado) return envelope; // legado: Blob em claro
  const iv = new Uint8Array(envelope.iv);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, _cryptoKey, envelope.ciphertext);
  return new Blob([plain], { type: envelope.type });
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
  // v2: store dedicado para a CryptoKey não-extraível (achado #19/2026-07-13).
  // Adição pura de tabela — Dexie migra instalações existentes sem callback.
  db.version(2).stores({
    cryptoKeys: "id",
  });

  return db;
}

/**
 * Adiciona item à fila de sincronização offline.
 */
async function enqueueSync(tipo, dados, fotos = []) {
  const database = await initDB();
  await ensureCryptoReady();
  // Fotos (Blob/File) cifradas com o mesmo padrão dos demais dados sensíveis
  // — antes eram persistidas em claro no IndexedDB (achado #19/2026-07-13).
  // Decifradas de volta em getPendingSync antes do upload.
  const fotosCifradas = await Promise.all(
    fotos.map(async (foto) => ({ ...foto, blob: await encryptBlob(foto.blob) })),
  );
  return database.syncQueue.add({
    tipo,
    // PII do payload (nomes, observação, GPS, pessoas, veículos) cifrada
    // at-rest no IndexedDB; decriptada em getPendingSync antes do envio (G3-2).
    dados: await encryptField(JSON.stringify(dados)),
    fotos: fotosCifradas,
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
  // antes do ensureCryptoReady do boot).
  if (items.length) {
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
    if (item.fotos && item.fotos.length) {
      item.fotos = await Promise.all(
        item.fotos.map(async (foto) => ({ ...foto, blob: await decryptBlob(foto.blob) })),
      );
    }
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
  await ensureCryptoReady();
  const encrypted = await Promise.all(pessoas.map(encryptPessoa));
  await database.pessoas.bulkPut(encrypted);
  _pessoasDecryptCache = null; // invalida o cache decriptado (dados mudaram)
}

/**
 * Cache local de veículos para autocomplete offline.
 * Campos sensíveis (placa, modelo, cor) são criptografados com AES-GCM,
 * mesmo padrão de pessoas (achado #19/2026-07-13).
 */
async function cacheVeiculos(veiculos) {
  const database = await initDB();
  await ensureCryptoReady();
  const encrypted = await Promise.all(veiculos.map(encryptVeiculo));
  await database.veiculos.bulkPut(encrypted);
  _veiculosDecryptCache = null; // invalida o cache decriptado (dados mudaram)
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
 * Busca veículos no cache local (descriptografa antes de filtrar).
 *
 * Placa/modelo cifrados (achado #19/2026-07-13) não podem mais ser filtrados
 * pelo índice nativo do Dexie — decripta o cache uma vez e reutiliza nas
 * buscas seguintes, mesmo padrão de memoização de searchPessoasLocal.
 */
async function searchVeiculosLocal(query) {
  const database = await initDB();
  const q = query.toUpperCase();
  if (_veiculosDecryptCache === null) {
    const all = await database.veiculos.toArray();
    _veiculosDecryptCache = await Promise.all(all.map(decryptVeiculo));
  }
  return _veiculosDecryptCache
    .filter((v) => v.placa.includes(q) || (v.modelo && v.modelo.toUpperCase().includes(q)))
    .slice(0, 10);
}
