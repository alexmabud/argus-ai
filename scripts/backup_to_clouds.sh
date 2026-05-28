#!/bin/bash
# backup_to_clouds.sh — Backup diário do Argus AI para Oracle Object Storage e Google Drive
#
# O que faz, em ordem:
#   1. Pega o dump mais recente do banco em /mnt/banco/backups → Oracle + GDrive
#   2. Cifra o .env com GPG simétrico (AES256) → Oracle + GDrive
#   3. Empacota /mnt/banco/grafana em tar.gz → Oracle + GDrive
#   4. Sincroniza /mnt/fotos → apenas GDrive (storage maior)
#   5. Aplica retenção (apaga arquivos remotos > 7 dias)
#   6. Atualiza métrica Prometheus de último backup bem-sucedido
#
# Pré-requisitos:
#   - rclone instalado e configurado com remotes "oracle" e "gdrive"
#   - gpg instalado
#   - Senha do GPG em /root/.argus_gpg_passphrase (chmod 600, owner root)
#   - Container db-backup gerando dumps diários em /mnt/banco/backups
#
# Cron sugerido (em /etc/cron.d/argus-backup-clouds, executado como root):
#   0 3 * * * root /home/ubuntu/argus-ai/scripts/backup_to_clouds.sh
#
# Logs em /var/log/argus_backup.log

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
BACKUP_DIR="/mnt/banco/backups"
ENV_FILE="/home/ubuntu/argus-ai/.env"
GRAFANA_DIR="/mnt/banco/grafana"
FOTOS_DIR="/mnt/fotos"
GPG_PASS_FILE="/root/.argus_gpg_passphrase"
RETENTION_DAYS=7
LOG_FILE="/var/log/argus_backup.log"
METRIC_FILE="/mnt/banco/textfile/backup_clouds.prom"

ORACLE_REMOTE="oracle:argus-backups"
GDRIVE_REMOTE="gdrive:Argus_Backups"

DATE=$(date +%Y%m%d)
RUN_ID="$(date +%Y-%m-%d_%H%M%S)"

# ── Helpers ──────────────────────────────────────────────────────────────────
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

abort() {
    log "ABORT: $*"
    exit 1
}

cleanup() {
    rm -f /tmp/argus_env_${DATE}.gpg /tmp/argus_grafana_${DATE}.tar.gz
}
trap cleanup EXIT

# ── Pre-flight ───────────────────────────────────────────────────────────────
log "=== Backup Argus AI → Clouds (run $RUN_ID) ==="

[ -f "$GPG_PASS_FILE" ] || abort "Arquivo de senha GPG não encontrado: $GPG_PASS_FILE"
[ "$(stat -c %a "$GPG_PASS_FILE")" = "600" ] || abort "Permissão errada em $GPG_PASS_FILE (deve ser 600)"
[ -f "$ENV_FILE" ] || abort ".env não encontrado: $ENV_FILE"
[ -d "$GRAFANA_DIR" ] || abort "Diretório Grafana não encontrado: $GRAFANA_DIR"
[ -d "$FOTOS_DIR" ] || abort "Diretório fotos não encontrado: $FOTOS_DIR"

command -v rclone >/dev/null || abort "rclone não instalado"
command -v gpg >/dev/null || abort "gpg não instalado"

rclone listremotes 2>/dev/null | grep -q '^oracle:' || abort "remote 'oracle' não configurado (rode 'rclone config')"
rclone listremotes 2>/dev/null | grep -q '^gdrive:' || abort "remote 'gdrive' não configurado (rode 'rclone config')"

# ── 1. Banco PostgreSQL (dump mais recente) ──────────────────────────────────
LATEST_DUMP=$(ls -1t "$BACKUP_DIR"/argus_*.dump 2>/dev/null | head -1)
[ -n "$LATEST_DUMP" ] || abort "Nenhum dump em $BACKUP_DIR (container db-backup rodando?)"

DUMP_BASENAME="argus_${DATE}.dump"
log "Banco: $LATEST_DUMP → $DUMP_BASENAME ($(du -h "$LATEST_DUMP" | cut -f1))"
rclone copyto "$LATEST_DUMP" "$ORACLE_REMOTE/banco/$DUMP_BASENAME" --log-level NOTICE
rclone copyto "$LATEST_DUMP" "$GDRIVE_REMOTE/banco/$DUMP_BASENAME" --log-level NOTICE

# ── 2. .env criptografado ────────────────────────────────────────────────────
ENV_GPG="/tmp/argus_env_${DATE}.gpg"
log "ENV: cifrando com GPG (AES256)"
gpg --batch --yes --passphrase-file "$GPG_PASS_FILE" \
    --cipher-algo AES256 \
    --symmetric \
    --output "$ENV_GPG" \
    "$ENV_FILE"

ENV_BASENAME="env_${DATE}.gpg"
log "ENV cifrado: $(du -h "$ENV_GPG" | cut -f1) → $ENV_BASENAME"
rclone copyto "$ENV_GPG" "$ORACLE_REMOTE/env/$ENV_BASENAME" --log-level NOTICE
rclone copyto "$ENV_GPG" "$GDRIVE_REMOTE/env/$ENV_BASENAME" --log-level NOTICE

# ── 3. Grafana ───────────────────────────────────────────────────────────────
GRAFANA_TAR="/tmp/argus_grafana_${DATE}.tar.gz"
log "Grafana: empacotando $GRAFANA_DIR"
tar -czf "$GRAFANA_TAR" -C "$(dirname "$GRAFANA_DIR")" "$(basename "$GRAFANA_DIR")"

GRAFANA_BASENAME="grafana_${DATE}.tar.gz"
log "Grafana: $(du -h "$GRAFANA_TAR" | cut -f1) → $GRAFANA_BASENAME"
rclone copyto "$GRAFANA_TAR" "$ORACLE_REMOTE/grafana/$GRAFANA_BASENAME" --log-level NOTICE
rclone copyto "$GRAFANA_TAR" "$GDRIVE_REMOTE/grafana/$GRAFANA_BASENAME" --log-level NOTICE

# ── 4. Fotos (apenas Google Drive — Oracle tem só 10GB) ──────────────────────
log "Fotos: sync $FOTOS_DIR → $GDRIVE_REMOTE/fotos/"
rclone sync "$FOTOS_DIR" "$GDRIVE_REMOTE/fotos/" \
    --transfers 4 \
    --checkers 8 \
    --log-level NOTICE \
    --exclude ".minio.sys/**" \
    --exclude "lost+found/**"

# ── 5. Retenção (apaga > RETENTION_DAYS dias em ambos os destinos) ───────────
log "Aplicando retenção: ${RETENTION_DAYS} dias para banco/env/grafana"
for prefix in banco env grafana; do
    for remote in "$ORACLE_REMOTE" "$GDRIVE_REMOTE"; do
        rclone delete "$remote/$prefix/" \
            --min-age "${RETENTION_DAYS}d" \
            --log-level NOTICE 2>>"$LOG_FILE" || true
    done
done
# Fotos NÃO têm retenção — é um mirror, deletar arquivo na origem some no destino via sync

# ── 6. Métrica Prometheus ────────────────────────────────────────────────────
TS=$(date +%s)
mkdir -p "$(dirname "$METRIC_FILE")"
cat > "${METRIC_FILE}.tmp" <<EOF
# HELP argus_backup_clouds_last_success_timestamp_seconds Unix timestamp do último backup para as nuvens bem-sucedido
# TYPE argus_backup_clouds_last_success_timestamp_seconds gauge
argus_backup_clouds_last_success_timestamp_seconds $TS
EOF
mv "${METRIC_FILE}.tmp" "$METRIC_FILE"
chmod 644 "$METRIC_FILE"

log "=== Backup concluído com sucesso (timestamp=$TS) ==="
