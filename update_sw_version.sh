#!/usr/bin/env bash
# Versiona o cache do Service Worker e os scripts/CSS do index.html
# com o hash do commit atual, garantindo cache-bust automático.
#
# Uso: bash ./update_sw_version.sh
#
# Executar ANTES de 'docker compose build'.
# Após o build, restaurar com:
#   git checkout frontend/sw.js frontend/index.html

set -euo pipefail

cd "$(dirname "$0")"

HASH=$(git rev-parse --short HEAD)
SW_FILE="frontend/sw.js"
INDEX_FILE="frontend/index.html"

if [ ! -f "$SW_FILE" ]; then
    echo "[sw-version] ERRO: $SW_FILE não encontrado." >&2
    exit 1
fi

if [ ! -f "$INDEX_FILE" ]; then
    echo "[sw-version] ERRO: $INDEX_FILE não encontrado." >&2
    exit 1
fi

sed -i "s/BUILD_HASH/${HASH}/g" "$SW_FILE"
echo "[sw-version] Service Worker versionado: argus-${HASH}"

# Reescreve todos os ?v=<algo> de .js/.css no index.html para o hash do commit.
# Cada deploy gera um hash novo => URL nova => bypassa cache HTTP do navegador.
sed -i -E "s#(\.(js|css))\?v=[a-zA-Z0-9]+#\1?v=${HASH}#g" "$INDEX_FILE"
echo "[sw-version] index.html versionado com cache-bust ?v=${HASH}"
