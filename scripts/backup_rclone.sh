#!/bin/bash
# backup_rclone.sh — Backup diário para Oracle Object Storage (10GB gratuito)
#
# O que faz:
#   1. Sincroniza fotos dos últimos 30 dias para Oracle Object Storage
#   2. Faz dump do PostgreSQL e envia para Object Storage
#   3. Mantém apenas os últimos 7 dumps no bucket
#
# Configuração do rclone (rodar uma vez manualmente):
#   rclone config
#   → New remote → nome: oracle-object
#   → Storage: s3 (Oracle é S3-compatible)
#   → Provider: Other
#   → env_auth: false
#   → access_key_id: (chave do Oracle Object Storage)
#   → secret_access_key: (secret do Oracle Object Storage)
#   → region: sa-saopaulo-1  (ajuste para sua região)
#   → endpoint: https://<namespace>.compat.objectstorage.<region>.oraclecloud.com
#   → Restante: Enter para padrão
#
# Cron diário (crontab -e):
#   0 3 * * * /opt/argus_ai/scripts/backup_rclone.sh >> /var/log/argus_backup.log 2>&1

set -euo pipefail

BUCKET="oracle-object:argus-backup"
FOTOS_DIR="/data/fotos"
BACKUP_DIR="/data/backups"
DB_USER="${DB_USER:-argus}"
DB_NAME="${DB_NAME:-argus_db}"
DB_CONTAINER="argus_ai-db-1"
RETENTION_DAYS=30
DUMP_RETENTION=7

DATE=$(date +%Y-%m-%d)
DUMP_FILE="$BACKUP_DIR/argus_db_$DATE.sql.gz"

echo "[$DATE] === Backup Argus AI iniciado ==="

# ── 1. Fotos recentes (últimos RETENTION_DAYS dias) ───────────────────────────
echo "[$DATE] Sincronizando fotos dos últimos $RETENTION_DAYS dias..."
rclone sync "$FOTOS_DIR" "$BUCKET/fotos" \
  --max-age "${RETENTION_DAYS}d" \
  --transfers 4 \
  --checkers 8 \
  --progress \
  --log-level INFO

echo "[$DATE] Fotos sincronizadas com sucesso."

# ── 2. Dump do banco de dados ─────────────────────────────────────────────────
echo "[$DATE] Gerando dump do PostgreSQL..."
mkdir -p "$BACKUP_DIR"
docker exec "$DB_CONTAINER" \
  pg_dump -U "$DB_USER" "$DB_NAME" \
  | gzip > "$DUMP_FILE"

echo "[$DATE] Dump gerado: $DUMP_FILE ($(du -sh "$DUMP_FILE" | cut -f1))"

# Upload do dump
rclone copy "$DUMP_FILE" "$BUCKET/dumps/" --log-level INFO
echo "[$DATE] Dump enviado para $BUCKET/dumps/"

# ── 3. Limpar dumps locais antigos ────────────────────────────────────────────
find "$BACKUP_DIR" -name "argus_db_*.sql.gz" -mtime "+$DUMP_RETENTION" -delete
echo "[$DATE] Dumps locais com mais de $DUMP_RETENTION dias removidos."

# ── 4. Limpar dumps remotos antigos ──────────────────────────────────────────
echo "[$DATE] Removendo dumps remotos antigos (mantendo últimos $DUMP_RETENTION)..."
rclone ls "$BUCKET/dumps/" \
  | sort \
  | head -n "-$DUMP_RETENTION" \
  | awk '{print $2}' \
  | xargs -I{} rclone deletefile "$BUCKET/dumps/{}" 2>/dev/null || true

echo "[$DATE] === Backup concluído com sucesso ==="
