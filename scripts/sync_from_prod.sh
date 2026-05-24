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
# Uso: make sync-from-prod
# ══════════════════════════════════════════════════════════════
set -euo pipefail

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

# ─── 4/6 ── Atualizar ENCRYPTION_KEY local ────────────────────
echo ""
echo "═══ 4/6 Atualizando ENCRYPTION_KEY local (chave de prod) ═══"
PROD_KEY=$(ssh "$SSH_HOST" "grep '^ENCRYPTION_KEY=' ~/argus-ai/.env" | cut -d= -f2-)
if [[ -z "$PROD_KEY" ]]; then
    echo "ERRO: nao foi possivel obter ENCRYPTION_KEY de prod" >&2
    exit 1
fi
sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$PROD_KEY|" "$ENV_FILE"
echo "ENCRYPTION_KEY atualizada para a chave de producao"

# ─── 5/6 ── Restore Postgres local ────────────────────────────
echo ""
echo "═══ 5/6 Restore do Postgres local ═══"
docker compose up -d db
# Espera DB ficar pronto
for i in {1..30}; do
    if docker exec argus-db pg_isready -U argus -d postgres >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
# Mata conexoes ativas e recria banco
docker exec argus-db psql -U argus -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='argus_db' AND pid<>pg_backend_pid();" >/dev/null
docker exec argus-db psql -U argus -d postgres -c "DROP DATABASE IF EXISTS argus_db;"
docker exec argus-db psql -U argus -d postgres -c "CREATE DATABASE argus_db OWNER argus;"
# Restore
docker exec -i argus-db pg_restore -U argus -d argus_db --no-owner --no-privileges < "$DUMP_FILE"
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
