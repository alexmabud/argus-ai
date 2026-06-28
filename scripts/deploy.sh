#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Script de deploy do Argus AI para Oracle Cloud (Ubuntu 22.04)
# HTTPS automático via Caddy (Let's Encrypt) — sem nginx/certbot.
# ══════════════════════════════════════════════════════════════
#
# Uso (primeira vez):
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh setup
#
# Uso (atualizações):
#   ./scripts/deploy.sh update
#
# ══════════════════════════════════════════════════════════════

set -euo pipefail

REPO_URL="https://github.com/alexmabud/argus-ai.git"
# Diretório canônico em prod: ~/argus-ai (o deploy real via CI faz `cd ~/argus-ai`
# e o nome do container argus-ai-db-1 confirma o basename argus-ai).
APP_DIR="$HOME/argus-ai"
COMPOSE_FILE="docker-compose.prod.yml"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
error() { echo "[ERRO] $*" >&2; exit 1; }

# ── Setup inicial (primeira vez) ─────────────────────────────
cmd_setup() {
    log "Iniciando setup do Argus AI..."

    # 1. Instalar Docker
    if ! command -v docker &>/dev/null; then
        log "Instalando Docker..."
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER"
        log "Docker instalado. Faça logout/login e execute novamente."
        exit 0
    fi

    # 2. Instalar Docker Compose plugin
    if ! docker compose version &>/dev/null; then
        log "Instalando Docker Compose plugin..."
        sudo apt-get update
        sudo apt-get install -y docker-compose-plugin
    fi

    # 3. Clonar repositório
    if [ ! -d "$APP_DIR" ]; then
        log "Clonando repositório..."
        git clone "$REPO_URL" "$APP_DIR"
    fi
    cd "$APP_DIR"

    # 4. Criar .env (arquivo lido pelo docker-compose.prod.yml via env_file)
    if [ ! -f .env ]; then
        log "Criando .env a partir do exemplo..."
        cp .env.production.example .env

        # Gerar chaves automaticamente. ENCRYPTION_KEY (Fernet) é obrigatória
        # para a criptografia LGPD — abortar se 'cryptography' não existir
        # (jamais gravar placeholder e seguir com chave inválida).
        SECRET_KEY=$(openssl rand -hex 32)
        if ! ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null); then
            error "python3 + 'cryptography' são necessários para gerar ENCRYPTION_KEY (LGPD). Instale: pip install cryptography"
        fi
        DB_PASSWORD=$(openssl rand -hex 16)

        sed -i "s/TROCAR-GERAR-COM-OPENSSL-RAND-HEX-32/$SECRET_KEY/" .env
        sed -i "s|TROCAR-GERAR-COM-FERNET|$ENCRYPTION_KEY|" .env
        sed -i "s/TROCAR-SENHA-FORTE-AQUI/$DB_PASSWORD/" .env

        log "Chaves SECRET_KEY/ENCRYPTION_KEY/DB_PASSWORD geradas em .env"
        log "IMPORTANTE: edite .env e defina as variáveis ainda obrigatórias"
        log "  (REDIS_PASSWORD, APP_DB_PASSWORD, S3_*, DOMAIN, LLM/CORS):"
        log "  nano .env"
    fi

    # 5. Build e start (Caddy provisiona TLS/HTTPS automaticamente)
    log "Fazendo build das imagens..."
    docker compose -f "$COMPOSE_FILE" build

    log "Iniciando serviços..."
    docker compose -f "$COMPOSE_FILE" up -d

    # 6. Rodar migrations (como DONO via MIGRATION_DATABASE_URL; alembic/env.py
    #    usa settings.effective_migration_url, não a DATABASE_URL de runtime argus_app).
    log "Aguardando banco ficar pronto..."
    sleep 10
    docker compose -f "$COMPOSE_FILE" exec -T api python -m alembic upgrade head \
        || error "Migrations falharam (alembic upgrade head). Deploy abortado — schema desatualizado."

    log "════════════════════════════════════════"
    log "Deploy concluído!"
    log "App disponível em https://<DOMAIN configurado no .env> (TLS automático via Caddy)"
    log "════════════════════════════════════════"
}

# ── Atualização (git pull + rebuild) ─────────────────────────
cmd_update() {
    cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado. Execute 'setup' primeiro."

    log "Atualizando Argus AI..."

    git fetch origin main
    git reset --hard origin/main

    log "Versionando Service Worker e cache-bust do index.html..."
    bash "${APP_DIR}/update_sw_version.sh"
    trap "git checkout frontend/sw.js frontend/index.html 2>/dev/null || true" EXIT

    log "Rebuilding imagens..."
    docker compose -f "$COMPOSE_FILE" build

    log "Reiniciando serviços..."
    docker compose -f "$COMPOSE_FILE" up -d

    # Migrations (como DONO via MIGRATION_DATABASE_URL — ver alembic/env.py)
    log "Executando migrations..."
    docker compose -f "$COMPOSE_FILE" exec -T api python -m alembic upgrade head \
        || error "Migrations falharam (alembic upgrade head). Atualização abortada."

    log "Atualização concluída!"
}

# ── Status dos serviços ──────────────────────────────────────
cmd_status() {
    cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado."
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    log "Logs recentes:"
    docker compose -f "$COMPOSE_FILE" logs --tail=20 api
}

# ── Logs ─────────────────────────────────────────────────────
cmd_logs() {
    cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado."
    docker compose -f "$COMPOSE_FILE" logs -f "${1:-api}"
}

# ── Main ─────────────────────────────────────────────────────
case "${1:-help}" in
    setup)  cmd_setup ;;
    update) cmd_update ;;
    status) cmd_status ;;
    logs)   cmd_logs "${2:-}" ;;
    *)
        echo "Uso: $0 {setup|update|status|logs}"
        echo ""
        echo "  setup           Primeiro deploy (instala Docker, clona, configura, sobe)"
        echo "  update          Atualiza (git pull, rebuild, restart, migrations)"
        echo "  status          Mostra status dos serviços"
        echo "  logs [serviço]  Mostra logs (padrão: api)"
        echo ""
        echo "  TLS/HTTPS é automático via Caddy (Let's Encrypt) — não há comando 'ssl'."
        ;;
esac
