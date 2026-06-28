# Pin por digest (manifest-list multi-arch) para builds reproduzíveis — o
# apt-get upgrade abaixo ainda aplica patches de CVE do OS por cima. Para
# atualizar a base: `docker buildx imagetools inspect pgvector/pgvector:pg16`.
FROM pgvector/pgvector:pg16@sha256:131dcf7ff6a900545df8e7e092c270aa8c6db2f2c818e408cb45ec21316b74e6

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
