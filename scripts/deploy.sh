#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Script de deploy do Argus AI para Oracle Cloud (Ubuntu 22.04)
# ══════════════════════════════════════════════════════════════
#
# Uso (primeira vez):
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh setup
#
# Uso (atualizações):
#   ./scripts/deploy.sh update
#
# Uso (SSL com Let's Encrypt):
#   ./scripts/deploy.sh ssl seu-dominio.com
#
# ══════════════════════════════════════════════════════════════

set -euo pipefail

REPO_URL="https://github.com/alexmabud/argus-ai.git"
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

    # 4. Verificar .env.production
    if [ ! -f .env.production ]; then
        log "Criando .env.production a partir do exemplo..."
        cp .env.production.example .env.production

        # Gerar chaves automaticamente
        SECRET_KEY=$(openssl rand -hex 32)
        ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "GERAR-MANUALMENTE")
        DB_PASSWORD=$(openssl rand -hex 16)

        sed -i "s/TROCAR-GERAR-COM-OPENSSL-RAND-HEX-32/$SECRET_KEY/" .env.production
        sed -i "s/TROCAR-GERAR-COM-FERNET/$ENCRYPTION_KEY/" .env.production
        sed -i "s/TROCAR-SENHA-FORTE-AQUI/$DB_PASSWORD/" .env.production

        log "Chaves geradas automaticamente em .env.production"
        log "IMPORTANTE: Edite .env.production para configurar S3, LLM e CORS"
        log "  nano .env.production"
    fi

    # 5. Usar nginx inicial (sem SSL)
    cp deploy/nginx-initial.conf deploy/nginx.conf

    # 6. Criar dirs para certbot
    mkdir -p deploy/certbot/conf deploy/certbot/www

    # 7. Build e start
    log "Fazendo build das imagens..."
    docker compose -f "$COMPOSE_FILE" build

    log "Iniciando serviços..."
    docker compose -f "$COMPOSE_FILE" up -d

    # 8. Rodar migrations
    log "Aguardando banco ficar pronto..."
    sleep 10
    docker compose -f "$COMPOSE_FILE" exec api python -m alembic upgrade head || \
        log "AVISO: Migrations falharam. Execute manualmente depois."

    log "════════════════════════════════════════"
    log "Deploy concluído!"
    log "API: http://$(curl -s ifconfig.me):80"
    log "Health: http://$(curl -s ifconfig.me):80/health"
    log "════════════════════════════════════════"
}

# ── Atualização (git pull + rebuild) ─────────────────────────
cmd_update() {
    cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado. Execute 'setup' primeiro."

    log "Atualizando Argus AI..."

    git pull origin main

    log "Rebuilding imagens..."
    docker compose -f "$COMPOSE_FILE" build

    log "Reiniciando serviços..."
    docker compose -f "$COMPOSE_FILE" up -d

    # Migrations
    log "Executando migrations..."
    docker compose -f "$COMPOSE_FILE" exec api python -m alembic upgrade head || \
        log "AVISO: Migrations falharam."

    log "Atualização concluída!"
}

# ── Configurar SSL com Let's Encrypt ─────────────────────────
cmd_ssl() {
    local domain="${1:-}"
    [ -z "$domain" ] && error "Uso: $0 ssl seu-dominio.com"

    cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado."

    log "Gerando certificado SSL para $domain..."

    # Gerar certificado
    docker compose -f "$COMPOSE_FILE" run --rm certbot \
        certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@"$domain" \
        --agree-tos \
        --no-eff-email \
        -d "$domain"

    # Trocar nginx config para versão com SSL
    sed "s/seu-dominio.com/$domain/g" deploy/nginx.conf.ssl > deploy/nginx.conf 2>/dev/null || \
        sed -i "s/seu-dominio.com/$domain/g" deploy/nginx.conf

    # Reload nginx
    docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

    log "SSL configurado para $domain!"
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
    ssl)    cmd_ssl "${2:-}" ;;
    status) cmd_status ;;
    logs)   cmd_logs "${2:-}" ;;
    *)
        echo "Uso: $0 {setup|update|ssl|status|logs}"
        echo ""
        echo "  setup           Primeiro deploy (instala Docker, clona, configura, sobe)"
        echo "  update          Atualiza (git pull, rebuild, restart, migrations)"
        echo "  ssl <dominio>   Configurar SSL com Let's Encrypt"
        echo "  status          Mostra status dos serviços"
        echo "  logs [serviço]  Mostra logs (padrão: api)"
        ;;
esac
