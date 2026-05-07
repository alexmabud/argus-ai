FROM pgvector/pgvector:pg16

# upgrade corrige CVEs do OS (incluindo CVE-2025-68121 score 10.0)
RUN set -eux; \
    apt-get update; \
    apt-get upgrade -y --no-install-recommends; \
    apt-get install -y --no-install-recommends \
      postgresql-16-postgis-3 \
      postgresql-16-postgis-3-scripts; \
    rm -rf /var/lib/apt/lists/*
