#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# fix_prod_cors.sh — Higieniza CORS_ORIGINS no .env de produção
# ══════════════════════════════════════════════════════════════
#
# O que faz (idempotente — pode rodar quantas vezes quiser):
#   1. Remove a origem residual http://<IP_DA_VM>:8000 (IP direto
#      sem TLS, resíduo de uma fase anterior em que a API era acessada
#      sem o Caddy na frente).
#   2. Força HTTPS na origem do domínio principal, trocando
#      http://arguseye.duckdns.org → https://arguseye.duckdns.org.
#      O Caddy já redireciona 80→443, então a entrada http:// é
#      sempre dead config, mas mantê-la fragiliza defesa em profundidade.
#
# Demais entradas no CORS_ORIGINS (capacitor://, outras origens
# legítimas que possam existir) são PRESERVADAS — o script só remove
# o IP conhecido e troca o esquema do domínio principal.
#
# Cria backup .env.bak.<timestamp> antes de qualquer alteração.
#
# Uso:
#   bash scripts/fix_prod_cors.sh [caminho/para/.env]
#
# Argumento opcional: caminho do arquivo .env (padrão: ./.env)
# ══════════════════════════════════════════════════════════════

set -euo pipefail

ENV_FILE="${1:-.env}"

# IP legado a remover do CORS_ORIGINS (origem residual sem TLS).
# Definir via env var ao chamar o script, ex.: LEGACY_IP=1.2.3.4 bash scripts/fix_prod_cors.sh
# Sem LEGACY_IP, o script só faz o ajuste http→https no domínio principal.
LEGACY_IP="${LEGACY_IP:-}"
DOMAIN="${DOMAIN:-arguseye.duckdns.org}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[fix_prod_cors] Arquivo não encontrado: $ENV_FILE" >&2
  exit 1
fi

BEFORE=$(grep '^CORS_ORIGINS' "$ENV_FILE" || true)

if [[ -z "$BEFORE" ]]; then
  echo "[fix_prod_cors] CORS_ORIGINS não encontrado em $ENV_FILE — nada a fazer."
  exit 0
fi

# Só altera o arquivo se houver algo pra limpar
NEEDS_IP_CLEANUP=0
if [[ -n "$LEGACY_IP" ]] && [[ "$BEFORE" == *"$LEGACY_IP"* ]]; then
  NEEDS_IP_CLEANUP=1
fi
if [[ $NEEDS_IP_CLEANUP -eq 0 ]] && [[ "$BEFORE" != *"http://$DOMAIN"* ]]; then
  echo "[fix_prod_cors] CORS_ORIGINS já está limpo, nada a fazer."
  echo "[fix_prod_cors] Valor atual: $BEFORE"
  exit 0
fi

BACKUP="${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP"
echo "[fix_prod_cors] Backup criado em: $BACKUP"

# Três variantes para cobrir vírgula antes, depois ou entrada isolada
SED_ARGS=()
if [[ $NEEDS_IP_CLEANUP -eq 1 ]]; then
  IP_ESC=$(echo "$LEGACY_IP" | sed 's/\./\\./g')
  SED_ARGS+=(
    -e "s|,[[:space:]]*\"http://${IP_ESC}:8000\"||g"
    -e "s|\"http://${IP_ESC}:8000\"[[:space:]]*,||g"
    -e "s|\"http://${IP_ESC}:8000\"||g"
  )
fi
DOMAIN_ESC=$(echo "$DOMAIN" | sed 's/\./\\./g')
SED_ARGS+=(-e "s|\"http://${DOMAIN_ESC}\"|\"https://${DOMAIN}\"|g")

sed -i "${SED_ARGS[@]}" "$ENV_FILE"

AFTER=$(grep '^CORS_ORIGINS' "$ENV_FILE" || echo "<não encontrado>")

echo "[fix_prod_cors] CORS_ORIGINS atualizado."
echo "[fix_prod_cors]   antes: $BEFORE"
echo "[fix_prod_cors]   agora: $AFTER"
