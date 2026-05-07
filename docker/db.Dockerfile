FROM pgvector/pgvector:pg16

# upgrade corrige CVEs de pacotes apt do OS
# CVEs golang/stdlib (ex: CVE-2025-68121) NÃO são corrigidos aqui — são binários
# Go compilados estaticamente na imagem base pgvector/pgvector:pg16 e dependem
# de atualização upstream do maintainer da imagem
RUN set -eux; \
    apt-get update; \
    apt-get upgrade -y --no-install-recommends; \
    apt-get install -y --no-install-recommends \
      postgresql-16-postgis-3 \
      postgresql-16-postgis-3-scripts; \
    rm -rf /var/lib/apt/lists/*
