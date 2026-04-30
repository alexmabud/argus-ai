#!/usr/bin/env bash
# Versiona o cache do Service Worker com o hash do commit atual.
#
# Uso: bash ./update_sw_version.sh
#
# Executar ANTES de 'docker compose build'.
# Após o build, restaurar com: git checkout frontend/sw.js

set -euo pipefail

cd "$(dirname "$0")"

HASH=$(git rev-parse --short HEAD)
SW_FILE="frontend/sw.js"

if [ ! -f "$SW_FILE" ]; then
    echo "[sw-version] ERRO: $SW_FILE não encontrado." >&2
    exit 1
fi

sed -i "s/BUILD_HASH/${HASH}/g" "$SW_FILE"
echo "[sw-version] Service Worker versionado: argus-${HASH}"
