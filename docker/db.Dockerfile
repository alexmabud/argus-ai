FROM postgis/postgis:16-3.4

# Install pgvector extension files in the Postgres image.
RUN set -eux; \
    apt-get update; \
    if apt-cache show postgresql-16-pgvector >/dev/null 2>&1; then \
      apt-get install -y --no-install-recommends postgresql-16-pgvector; \
    else \
      apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        build-essential \
        postgresql-server-dev-16; \
      git clone --branch v0.8.1 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector; \
      cd /tmp/pgvector; \
      make; \
      make install; \
      rm -rf /tmp/pgvector; \
    fi; \
    rm -rf /var/lib/apt/lists/*
