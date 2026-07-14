#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Argus AI — Sincronizar dados de produção para ambiente local
# ══════════════════════════════════════════════════════════════
# Espelha o banco Postgres + fotos do MinIO da VM para a maquina
# local, permitindo testar com dados reais sem subir pra producao.
#
# ATENCAO LGPD: o dump contem CPFs criptografados e dados pessoais
# reais. A maquina local passa a guardar dados sensiveis — mantenha
# acesso restrito e criptografia de disco habilitada.
#
# Por padrao a ENCRYPTION_KEY de PRODUCAO NAO e copiada para o dev
# (mantem/gera uma chave local) — os CPFs do dump ficam ilegiveis.
# Use a flag --with-prod-key (make sync-from-prod KEY=1) para tambem
# trazer a chave-mestra de prod e decifrar os CPFs localmente.
#
# Uso: make sync-from-prod            (default seguro, sem chave de prod)
#      make sync-from-prod KEY=1      (opt-in: traz a chave de prod)
# ══════════════════════════════════════════════════════════════
set -euo pipefail

WITH_PROD_KEY=0
for arg in "$@"; do
    case "$arg" in
        --with-prod-key) WITH_PROD_KEY=1 ;;
    esac
done

SSH_HOST="argus"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SYNC_DIR="$PROJECT_DIR/tmp/sync"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
DUMP_FILE="$SYNC_DIR/argus_db.dump"
FOTOS_DIR="$SYNC_DIR/fotos"
ENV_FILE="$PROJECT_DIR/.env"
ENV_BACKUP="$PROJECT_DIR/.env.bak.$TIMESTAMP"

mkdir -p "$SYNC_DIR" "$FOTOS_DIR"

echo "════════════════════════════════════════════════════════"
echo " Argus AI — Sync de PRODUCAO -> LOCAL"
echo "════════════════════════════════════════════════════════"
echo " Servidor : $SSH_HOST"
echo " Destino  : $PROJECT_DIR"
echo " Timestamp: $TIMESTAMP"
echo ""
echo " ATENCAO: vai SUBSTITUIR o banco local 'argus_db' e o"
echo " conteudo do MinIO local pelos dados de PRODUCAO."
echo ""
read -p " Continuar? [s/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 0
fi

# Confirmação SEPARADA e explícita para --with-prod-key: a chave-mestra de
# produção decifrando CPFs numa máquina de dev é o item de maior impacto
# LGPD deste script — não deve passar despercebido dentro do "Continuar?"
# genérico acima, nem só por causa de um alias/muscle-memory com KEY=1
# (achado #10/2026-07-13).
if [[ "$WITH_PROD_KEY" == "1" ]]; then
    echo ""
    echo " ⚠️  --with-prod-key: a ENCRYPTION_KEY de PRODUCAO sera copiada para este"
    echo "    dispositivo, tornando os CPFs do dump DECIFRAVEIS localmente."
    echo ""
    read -p " Confirma trazer a chave-mestra de producao? [s/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Cancelado."
        exit 0
    fi
fi

# ─── 1/6 ── pg_dump na VM ─────────────────────────────────────
echo ""
echo "═══ 1/6 pg_dump no servidor ═══"
ssh "$SSH_HOST" "docker exec argus-ai-db-1 pg_dump -U argus -Fc argus_db" > "$DUMP_FILE"
DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "Dump salvo em $DUMP_FILE ($DUMP_SIZE)"

# ─── 2/6 ── rsync /mnt/fotos ──────────────────────────────────
echo ""
echo "═══ 2/6 rsync das fotos (MinIO) ═══"
rsync -avz --delete --info=progress2 \
    --rsync-path="sudo rsync" \
    "$SSH_HOST:/mnt/fotos/" "$FOTOS_DIR/"

# ─── 3/6 ── Backup do .env local ──────────────────────────────
echo ""
echo "═══ 3/6 Backup do .env local ═══"
cp "$ENV_FILE" "$ENV_BACKUP"
echo "Backup salvo em $ENV_BACKUP"

# ─── 4/6 ── ENCRYPTION_KEY local ──────────────────────────────
echo ""
if [[ "$WITH_PROD_KEY" == "1" ]]; then
    echo "═══ 4/6 Trazendo ENCRYPTION_KEY de PRODUCAO (opt-in --with-prod-key) ═══"
    PROD_KEY=$(ssh "$SSH_HOST" "grep '^ENCRYPTION_KEY=' ~/argus-ai/.env" | cut -d= -f2-)
    if [[ -z "$PROD_KEY" ]]; then
        echo "ERRO: nao foi possivel obter ENCRYPTION_KEY de prod" >&2
        exit 1
    fi
    sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$PROD_KEY|" "$ENV_FILE"
    echo "ENCRYPTION_KEY atualizada para a chave de producao"
else
    echo "═══ 4/6 ENCRYPTION_KEY local (chave de prod NAO copiada) ═══"
    if grep -qE '^ENCRYPTION_KEY=.+' "$ENV_FILE"; then
        echo "Mantendo a ENCRYPTION_KEY local existente."
    else
        PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
        [[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="python3"
        NOVA_KEY=$("$PYTHON_BIN" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        if grep -q '^ENCRYPTION_KEY=' "$ENV_FILE"; then
            sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$NOVA_KEY|" "$ENV_FILE"
        else
            printf '\nENCRYPTION_KEY=%s\n' "$NOVA_KEY" >> "$ENV_FILE"
        fi
        echo "Gerada nova ENCRYPTION_KEY local."
    fi
    echo "ATENCAO: os CPFs do dump foram cifrados com a chave de PROD e ficarao"
    echo "ILEGIVEIS localmente. Rode 'make sync-from-prod KEY=1' se precisar decifra-los."
fi

# ─── 5/6 ── Restore Postgres local ────────────────────────────
echo ""
echo "═══ 5/6 Restore do Postgres local ═══"
docker compose up -d db
# Espera DB ficar pronto — aborta (não segue mudo) se nunca ficar pronto,
# senão os comandos seguintes falham com erro de conexão confuso em vez de
# uma mensagem clara (achado #10/2026-07-13).
DB_PRONTO=0
for i in {1..30}; do
    if docker exec argus-db pg_isready -U argus -d postgres >/dev/null 2>&1; then
        DB_PRONTO=1
        break
    fi
    sleep 1
done
if [[ "$DB_PRONTO" != "1" ]]; then
    echo "ERRO: Postgres local não ficou pronto em 30s — abortando antes de tocar no banco." >&2
    exit 1
fi
# Mata conexoes ativas e recria banco
docker exec argus-db psql -U argus -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='argus_db' AND pid<>pg_backend_pid();" >/dev/null
docker exec argus-db psql -U argus -d postgres -c "DROP DATABASE IF EXISTS argus_db;"
docker exec argus-db psql -U argus -d postgres -c "CREATE DATABASE argus_db OWNER argus;"
# Restore — captura o rc (|| ...=$?) em vez de deixar o `set -e` abortar no
# meio: sem isso, uma falha aqui deixava o banco local DROPADO e recriado
# vazio (ou parcialmente restaurado), sem nenhuma mensagem acionável
# (mesmo padrão de restore_from_backup.sh, achado #10/2026-07-13).
restore_rc=0
docker exec -i argus-db pg_restore -U argus -d argus_db --no-owner --no-privileges < "$DUMP_FILE" || restore_rc=$?
if [[ "$restore_rc" != "0" ]]; then
    echo "ERRO: pg_restore falhou (rc=$restore_rc) — banco local 'argus_db' pode estar vazio ou" >&2
    echo "  parcialmente restaurado. Rode o sync de novo, ou restaure manualmente a partir de" >&2
    echo "  $DUMP_FILE." >&2
    exit 1
fi
echo "Postgres restaurado"

# ─── 6/6 ── Restore MinIO local ───────────────────────────────
echo ""
echo "═══ 6/6 Restore do MinIO local ═══"
docker compose stop minio
docker run --rm \
    -v argus_ai_minio_data:/data \
    -v "$FOTOS_DIR:/src:ro" \
    alpine sh -c "rm -rf /data/* /data/.minio.sys 2>/dev/null || true; cp -a /src/. /data/"
docker compose up -d minio
# Reexecuta o init de buckets/politicas (mc mb/anonymous set none) mesmo
# apos a copia bruta dos arquivos — o .minio.sys copiado de prod nem sempre
# preserva o estado de bucket/policy esperado pelo compose local, e sem
# reexecutar o init isso falha silenciosamente (achado #10/2026-07-13).
docker compose up -d minio-init
echo "MinIO restaurado"

echo ""
echo "════════════════════════════════════════════════════════"
echo " ✅ Sync concluido em $(date +%H:%M:%S)"
echo "════════════════════════════════════════════════════════"
echo " Backup do .env anterior: $ENV_BACKUP"
echo " Dump salvo em:           $DUMP_FILE"
echo " Fotos sincronizadas em:  $FOTOS_DIR"
echo ""
echo " Proximos passos: 'make dev' para subir a API local"
echo "════════════════════════════════════════════════════════"

# ─── Limpeza de backups antigos do .env (chaves rotacionadas) ──
# Mantem apenas o backup recem-criado ($ENV_BACKUP) como rollback.
# Backups mais antigos contem ENCRYPTION_KEYs anteriores que so
# servem como vetor de ataque sobre eventuais dumps antigos.
shopt -s nullglob
ENV_BAK_ANTIGOS=()
for f in "$PROJECT_DIR"/.env.bak.*; do
    if [[ "$f" != "$ENV_BACKUP" ]]; then
        ENV_BAK_ANTIGOS+=("$f")
    fi
done
if [[ ${#ENV_BAK_ANTIGOS[@]} -gt 0 ]]; then
    echo ""
    echo "Removendo ${#ENV_BAK_ANTIGOS[@]} backup(s) antigo(s) de .env (chaves rotacionadas)..."
    shred -u "${ENV_BAK_ANTIGOS[@]}" 2>/dev/null || rm -f "${ENV_BAK_ANTIGOS[@]}"
fi

# ─── Aviso de seguranca LGPD ──────────────────────────────────
if [[ "$WITH_PROD_KEY" == "1" ]]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo " ATENCAO: .env local agora contem a ENCRYPTION_KEY de PRODUCAO."
    echo " Se este device for perdido ou comprometido, CPFs da base ficam"
    echo " decifraveis. Exija criptografia de disco (LUKS/BitLocker) e"
    echo " bloqueio automatico de tela."
    echo "═══════════════════════════════════════════════════════════════"
fi
