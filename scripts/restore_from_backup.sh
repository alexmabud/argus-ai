#!/bin/bash
# restore_from_backup.sh — Restauração interativa do Argus AI a partir dos backups na nuvem
#
# Lista backups disponíveis em Oracle Object Storage ou Google Drive,
# pergunta qual data restaurar e o que restaurar (banco, env, grafana, fotos
# ou tudo), e executa o restore. Nada destrutivo sem confirmação explícita.
#
# Pré-requisitos:
#   - rclone instalado e configurado com remotes "oracle" e "gdrive"
#   - gpg instalado (para decifrar o .env)
#   - Senha do GPG conhecida (será solicitada quando descriptografar)
#
# Uso:
#   sudo ./scripts/restore_from_backup.sh
#
# IMPORTANTE: rode SEMPRE com sudo — restore mexe em arquivos protegidos
# (/mnt/banco/grafana, /mnt/fotos) e precisa parar/iniciar containers.

set -euo pipefail

ORACLE_REMOTE="oracle:argus-backups"
GDRIVE_REMOTE="gdrive:Argus_Backups"
ARGUS_DIR="/home/ubuntu/argus-ai"
WORK_DIR="/tmp/argus_restore_$$"

mkdir -p "$WORK_DIR"
trap "rm -rf $WORK_DIR" EXIT

# ── Helpers ──────────────────────────────────────────────────────────────────
say()    { echo -e "\033[1;36m[restore]\033[0m $*"; }
warn()   { echo -e "\033[1;33m[restore]\033[0m $*"; }
err()    { echo -e "\033[1;31m[restore]\033[0m $*"; }
ok()     { echo -e "\033[1;32m[restore]\033[0m $*"; }
confirm() {
    local prompt="$1"
    read -r -p "$prompt [s/N] " resp
    [[ "$resp" =~ ^[sSyY]$ ]]
}

# ── Pré-checks ───────────────────────────────────────────────────────────────
[ "$(id -u)" = "0" ] || { err "Rode com sudo"; exit 1; }
command -v rclone >/dev/null || { err "rclone não instalado"; exit 1; }
command -v gpg >/dev/null || { err "gpg não instalado"; exit 1; }

# ── 1. Escolher origem ───────────────────────────────────────────────────────
say "De onde restaurar?"
echo "  1) Oracle Object Storage   (banco, env, grafana)"
echo "  2) Google Drive            (banco, env, grafana, fotos)"
read -r -p "Escolha [1-2]: " src_choice

case "$src_choice" in
    1) REMOTE="$ORACLE_REMOTE"; HAS_FOTOS=false ;;
    2) REMOTE="$GDRIVE_REMOTE"; HAS_FOTOS=true ;;
    *) err "Opção inválida"; exit 1 ;;
esac

say "Origem: $REMOTE"

# ── 2. Listar backups disponíveis ────────────────────────────────────────────
say "Listando backups de banco disponíveis..."
rclone ls "$REMOTE/banco/" 2>/dev/null | awk '{print $2}' | sort

read -r -p "Qual data restaurar? (formato YYYYMMDD, ex: 20260527): " RESTORE_DATE
[[ "$RESTORE_DATE" =~ ^[0-9]{8}$ ]] || { err "Formato inválido"; exit 1; }

# ── 3. Escolher o que restaurar ──────────────────────────────────────────────
say "O que restaurar?"
echo "  1) Banco (Postgres dump)"
echo "  2) .env (com decifragem GPG)"
echo "  3) Grafana (configs/dashboards/anotações)"
if [ "$HAS_FOTOS" = true ]; then
    echo "  4) Fotos (espelho de /mnt/fotos)"
    echo "  5) Tudo (1+2+3+4)"
else
    echo "  5) Tudo (1+2+3)"
fi
read -r -p "Escolha (pode ser múltiplo separado por vírgula, ex: 1,2,3): " ITEMS

DO_BANCO=false; DO_ENV=false; DO_GRAFANA=false; DO_FOTOS=false
IFS=',' read -ra arr <<< "$ITEMS"
for n in "${arr[@]}"; do
    case "$n" in
        1) DO_BANCO=true ;;
        2) DO_ENV=true ;;
        3) DO_GRAFANA=true ;;
        4) [ "$HAS_FOTOS" = true ] && DO_FOTOS=true ;;
        5) DO_BANCO=true; DO_ENV=true; DO_GRAFANA=true; [ "$HAS_FOTOS" = true ] && DO_FOTOS=true ;;
    esac
done

# ── 4. Resumo + confirmação ──────────────────────────────────────────────────
say "Resumo:"
echo "  Origem    : $REMOTE"
echo "  Data      : $RESTORE_DATE"
echo "  Banco     : $DO_BANCO"
echo "  .env      : $DO_ENV"
echo "  Grafana   : $DO_GRAFANA"
echo "  Fotos     : $DO_FOTOS"
echo
warn "RESTAURAR sobrescreve dados em produção. Tem certeza?"
confirm "Continuar?" || { say "Cancelado."; exit 0; }

# ── 5. Banco ─────────────────────────────────────────────────────────────────
if [ "$DO_BANCO" = true ]; then
    DUMP_FILE="$WORK_DIR/argus_${RESTORE_DATE}.dump"
    say "Baixando dump do banco..."
    rclone copy "$REMOTE/banco/argus_${RESTORE_DATE}.dump" "$WORK_DIR/" --log-level NOTICE
    [ -f "$DUMP_FILE" ] || { err "Dump não baixou: $DUMP_FILE"; exit 1; }

    warn "Vou DROPAR e RECRIAR o banco argus_db. Toda alteração depois de $RESTORE_DATE será perdida."
    confirm "Continuar com o restore do banco?" || { say "Pulando banco."; DO_BANCO=false; }
fi

if [ "$DO_BANCO" = true ]; then
    say "Parando API e worker para destravar conexões..."
    docker compose -f "$ARGUS_DIR/docker-compose.prod.yml" stop api worker || true

    say "Restaurando dump no container do Postgres..."
    # Captura o resultado (|| ...=$?) para que set -e NÃO aborte antes de religar
    # API/worker — senão uma falha de pg_restore deixaria a produção parada.
    restore_rc=0
    docker exec -i argus-ai-db-1 pg_restore -U argus -d argus_db --clean --if-exists --no-owner --no-acl < "$DUMP_FILE" || restore_rc=$?

    say "Reiniciando API e worker..."
    docker compose -f "$ARGUS_DIR/docker-compose.prod.yml" start api worker || true

    if [ "$restore_rc" -ne 0 ]; then
        err "pg_restore falhou (rc=$restore_rc) — API/worker religados; banco pode estar inconsistente."
        exit 1
    fi
    ok "Banco restaurado de $RESTORE_DATE"
fi

# ── 6. .env ─────────────────────────────────────────────────────────────────
if [ "$DO_ENV" = true ]; then
    ENV_GPG="$WORK_DIR/env_${RESTORE_DATE}.gpg"
    say "Baixando .env cifrado..."
    rclone copy "$REMOTE/env/env_${RESTORE_DATE}.gpg" "$WORK_DIR/" --log-level NOTICE

    say "Decifrando .env (vai pedir a senha GPG salva no seu cofre de senhas)..."
    gpg --batch --yes --output "$WORK_DIR/.env" --decrypt "$ENV_GPG" || {
        err "Falha ao decifrar — senha errada?"
        exit 1
    }

    warn ".env atual será substituído. Backup em ${ARGUS_DIR}/.env.bkp.$(date +%s)"
    confirm "Continuar com o restore do .env?" || { say "Pulando .env."; DO_ENV=false; }
fi

if [ "$DO_ENV" = true ]; then
    cp "$ARGUS_DIR/.env" "$ARGUS_DIR/.env.bkp.$(date +%s)" 2>/dev/null || true
    cp "$WORK_DIR/.env" "$ARGUS_DIR/.env"
    chown ubuntu:ubuntu "$ARGUS_DIR/.env"
    chmod 600 "$ARGUS_DIR/.env"
    ok ".env restaurado de $RESTORE_DATE (backup anterior em .env.bkp.*)"
fi

# ── 7. Grafana ──────────────────────────────────────────────────────────────
if [ "$DO_GRAFANA" = true ]; then
    GR_TAR="$WORK_DIR/grafana_${RESTORE_DATE}.tar.gz"
    say "Baixando backup do Grafana..."
    rclone copy "$REMOTE/grafana/grafana_${RESTORE_DATE}.tar.gz" "$WORK_DIR/" --log-level NOTICE

    warn "Vou parar o container Grafana, sobrescrever /mnt/banco/grafana e reiniciar."
    confirm "Continuar com o restore do Grafana?" || { say "Pulando Grafana."; DO_GRAFANA=false; }
fi

if [ "$DO_GRAFANA" = true ]; then
    docker compose -f "$ARGUS_DIR/docker-compose.monitoring.yml" stop grafana || true
    # Extrai para uma área de staging ANTES de mexer no diretório ativo: se o tar
    # estiver corrompido, o /mnt/banco/grafana atual é preservado (antes, o mv
    # acontecia antes do tar e uma falha deixava o Grafana sem dados).
    rm -rf /mnt/banco/grafana.staging
    mkdir -p /mnt/banco/grafana.staging
    if tar -xzf "$GR_TAR" -C /mnt/banco/grafana.staging; then
        rm -rf /mnt/banco/grafana.old
        mv /mnt/banco/grafana /mnt/banco/grafana.old
        mv /mnt/banco/grafana.staging/grafana /mnt/banco/grafana
        rm -rf /mnt/banco/grafana.staging
        chown -R 472:472 /mnt/banco/grafana
        docker compose -f "$ARGUS_DIR/docker-compose.monitoring.yml" start grafana || true
        ok "Grafana restaurado de $RESTORE_DATE (snapshot anterior em /mnt/banco/grafana.old)"
    else
        rm -rf /mnt/banco/grafana.staging
        docker compose -f "$ARGUS_DIR/docker-compose.monitoring.yml" start grafana || true
        err "Falha ao extrair o tar do Grafana — diretório atual preservado, Grafana religado."
        exit 1
    fi
fi

# ── 8. Fotos (apenas Google Drive) ───────────────────────────────────────────
if [ "$DO_FOTOS" = true ]; then
    warn "Vou sincronizar GDrive → /mnt/fotos. Arquivos locais que não estão no GDrive serão APAGADOS."
    confirm "Continuar com o restore das fotos?" || { say "Pulando fotos."; DO_FOTOS=false; }
fi

if [ "$DO_FOTOS" = true ]; then
    say "Sincronizando GDrive → /mnt/fotos..."
    rclone sync "$GDRIVE_REMOTE/fotos/" /mnt/fotos/ \
        --transfers 4 \
        --checkers 8 \
        --log-level NOTICE
    ok "Fotos restauradas"
fi

ok "Restore concluído. Verifique a aplicação."
