FROM python:3.11-slim

# supercronic: cron para containers, sem setpgid/privilege issues (Alpine crond quebra no ARM64)
# Build roda no servidor ARM64 — binário arm64. Checksum verificado (supply chain).
ARG SUPERCRONIC_VERSION=v0.2.29
ARG SUPERCRONIC_SHA256=063799a43c1eac082d83ac59a43a6896b50d69aa1f533c2cc6a5376cb2bfff89
RUN apt-get update && apt-get install -y --no-install-recommends curl tzdata \
    && curl -fsSL \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-arm64" \
       -o /usr/local/bin/supercronic \
    && echo "${SUPERCRONIC_SHA256}  /usr/local/bin/supercronic" | sha256sum -c - \
    && chmod +x /usr/local/bin/supercronic \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Sao_Paulo

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY daily_report.py .

# Cron: todo dia às 8h BRT (= 11h UTC)
RUN echo "0 8 * * * /usr/local/bin/python /app/daily_report.py" > /etc/crontab

CMD ["supercronic", "/etc/crontab"]
