#!/usr/bin/env bash
# =============================================================================
# security_check.sh — Verificação de segurança Argus AI
#
# Checagens read-only do estado de segurança em produção.
# Proxy: Caddy (não Nginx). DB: Postgres em container Docker.
# Adaptar CONTAINER_* abaixo conforme docker-compose.prod.yml.
#
# Uso: bash scripts/security_check.sh
# =============================================================================
set -euo pipefail

CONTAINER_DB="argus-db"
CONTAINER_API="argus-api"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
sep()  { echo -e "\n${BLUE}══════════════════════════════════════${NC}"; }

ERROS=0

sep
echo -e "${BLUE}Argus AI — Verificação de Segurança${NC}"
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
sep

# ─── 1. Portas expostas ────────────────────────────────────────────────────────
echo -e "\n${BLUE}[1] Portas escutando externamente${NC}"

if command -v ss &>/dev/null; then
    # Postgres (5432) não deve estar exposto externamente — apenas 127.0.0.1
    if ss -tlnp 2>/dev/null | grep -qE "0\.0\.0\.0:5432|:::5432"; then
        fail "Postgres exposto em 0.0.0.0:5432 — deve ser 127.0.0.1 apenas"
        ERROS=$((ERROS + 1))
    else
        ok "Postgres não exposto externamente"
    fi

    # Redis (6379) não deve estar exposto externamente
    if ss -tlnp 2>/dev/null | grep -qE "0\.0\.0\.0:6379|:::6379"; then
        fail "Redis exposto em 0.0.0.0:6379 — deve ser 127.0.0.1 apenas"
        ERROS=$((ERROS + 1))
    else
        ok "Redis não exposto externamente"
    fi

    # HTTP/HTTPS (443) deve estar escutando (Caddy)
    if ss -tlnp 2>/dev/null | grep -qE ":443"; then
        ok "Porta 443 (HTTPS/Caddy) ativa"
    else
        warn "Porta 443 não encontrada — Caddy está rodando?"
    fi
else
    warn "ss não disponível — checar portas manualmente"
fi

# ─── 2. Containers Docker ────────────────────────────────────────────────────────
sep
echo -e "\n${BLUE}[2] Containers Docker${NC}"

if command -v docker &>/dev/null; then
    for container in argus-db argus-api argus-redis argus-caddy argus-minio; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
            ok "Container ${container} está rodando"
        else
            warn "Container ${container} não encontrado"
        fi
    done
else
    warn "Docker não disponível neste ambiente"
fi

# ─── 3. Banco de dados — conexões por usuário ─────────────────────────────────
sep
echo -e "\n${BLUE}[3] Conexões PostgreSQL por usuário${NC}"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_DB}$"; then
    docker exec "${CONTAINER_DB}" psql -U argus -d argus_db -c \
        "SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename ORDER BY count DESC;" \
        2>/dev/null && ok "Consulta de conexões OK" || warn "Falha ao consultar conexões PG"

    # Superusuário postgres não deve ter conexões de app
    PG_SUPER=$(docker exec "${CONTAINER_DB}" psql -U argus -d argus_db -tAc \
        "SELECT count(*) FROM pg_stat_activity WHERE usename='postgres' AND application_name != 'psql';" \
        2>/dev/null || echo "0")
    if [ "${PG_SUPER:-0}" -gt 0 ]; then
        fail "Superusuário 'postgres' com ${PG_SUPER} conexões de app ativas"
        ERROS=$((ERROS + 1))
    else
        ok "Superusuário postgres sem conexões de app"
    fi
else
    warn "Container ${CONTAINER_DB} não encontrado — checagem PG ignorada"
fi

# ─── 4. Senhas provisórias expiradas sem uso ─────────────────────────────────
sep
echo -e "\n${BLUE}[4] Senhas provisórias expiradas e não utilizadas${NC}"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_DB}$"; then
    EXPIRADAS=$(docker exec "${CONTAINER_DB}" psql -U argus -d argus_db -tAc \
        "SELECT count(*) FROM usuarios WHERE senha_expira_em < NOW() AND ativo = true;" \
        2>/dev/null || echo "N/A")
    if [ "${EXPIRADAS}" = "0" ] || [ "${EXPIRADAS}" = "N/A" ]; then
        ok "Nenhuma senha provisória expirada sem uso (${EXPIRADAS})"
    else
        warn "${EXPIRADAS} usuário(s) com senha provisória expirada — considerar gerar nova"
    fi
else
    warn "Container DB não acessível — checagem ignorada"
fi

# ─── 5. Últimos logins (audit_logs) ──────────────────────────────────────────
sep
echo -e "\n${BLUE}[5] Últimos 10 logins (audit_logs)${NC}"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_DB}$"; then
    docker exec "${CONTAINER_DB}" psql -U argus -d argus_db -c \
        "SELECT timestamp, usuario_id, ip_address FROM audit_logs
         WHERE acao = 'LOGIN' ORDER BY timestamp DESC LIMIT 10;" \
        2>/dev/null || warn "Falha ao consultar audit_logs"
else
    warn "Container DB não acessível — checagem ignorada"
fi

# ─── 6. Falhas SSH recentes ───────────────────────────────────────────────────
sep
echo -e "\n${BLUE}[6] Falhas SSH recentes (/var/log/auth.log)${NC}"

if [ -f /var/log/auth.log ]; then
    SSH_FALHAS=$(grep -c "Failed password" /var/log/auth.log 2>/dev/null || echo "0")
    if [ "${SSH_FALHAS}" -gt 100 ]; then
        warn "${SSH_FALHAS} falhas SSH em auth.log — possível brute-force"
    else
        ok "${SSH_FALHAS} falhas SSH (normal)"
    fi
    grep "Failed password" /var/log/auth.log 2>/dev/null | tail -5 || true
elif [ -f /var/log/secure ]; then
    grep "Failed password" /var/log/secure 2>/dev/null | tail -5 || true
else
    info "auth.log não encontrado — verificar journald: journalctl -u ssh --since '1h ago'"
fi

# ─── 7. fail2ban (SSH) ───────────────────────────────────────────────────────
sep
echo -e "\n${BLUE}[7] fail2ban status (SSH)${NC}"

if command -v fail2ban-client &>/dev/null; then
    fail2ban-client status sshd 2>/dev/null || warn "fail2ban sshd não configurado"
else
    info "fail2ban não instalado"
fi

# ─── 8. Caddy — verificação básica ───────────────────────────────────────────
sep
echo -e "\n${BLUE}[8] Caddy${NC}"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "argus-caddy"; then
    ok "Container Caddy rodando"
elif command -v caddy &>/dev/null; then
    ok "Caddy instalado localmente"
else
    warn "Caddy não encontrado como container nem instalado"
fi

# ─── 9. Resumo ───────────────────────────────────────────────────────────────
sep
echo -e "\n${BLUE}[RESUMO]${NC}"
if [ "${ERROS}" -eq 0 ]; then
    echo -e "${GREEN}✓ Nenhum problema crítico encontrado${NC}"
else
    echo -e "${RED}✗ ${ERROS} problema(s) crítico(s) encontrado(s) — revisar acima${NC}"
    exit 1
fi
