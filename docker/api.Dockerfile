# ══════════════════════════════════════════════════════════════
# Dockerfile de DESENVOLVIMENTO — não é a fonte da verdade de produção.
# Diferenças intencionais vs. Dockerfile.prod (achado #29/2026-07-13):
#   - Single-stage (sem separar build/runtime): a imagem final carrega
#     build-essential/toolchain de compilação. Aceito em dev — rebuild
#     rápido ao trocar dependência nativa importa mais que o tamanho da
#     imagem, que nunca sai da máquina do dev / CI local.
#   - `pip install ".[vision]"` resolve contra os RANGES do pyproject.toml,
#     não requirements.lock com hashes. Também intencional: forçar o dev a
#     regenerar o lock (`make lock`) só para testar uma versão nova de uma
#     lib travaria a iteração. requirements.lock/--require-hashes é
#     exclusivo do build de produção (Dockerfile.prod), que É a fonte da
#     verdade do que roda em produção.
#   - Base image por tag (`python:3.12-slim-bookworm`), não por digest —
#     mesma política do Dockerfile.prod (nenhum dos dois pina digest hoje).
#     Compensação: Dockerfile.prod roda `apt-get upgrade` a cada build,
#     então CVEs de pacote do SO são corrigidas no rebuild independente do
#     digest da base estar "velho".
# ══════════════════════════════════════════════════════════════
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Torch CPU-only (pinado igual ao lock) evita baixar CUDA (~3GB) e triton (~400MB).
# Dev instala o extra [vision] (insightface/easyocr/onnxruntime) para ter
# reconhecimento facial e OCR também em desenvolvimento.
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir torch==2.12.0 torchvision==0.27.0 --index-url https://download.pytorch.org/whl/cpu && \
    python -m pip install --no-cache-dir ".[vision]"

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# /health/ready testa DB + Redis de verdade (achado #29/2026-07-13) — /health
# sozinho "mentia" saudável mesmo com o banco fora do ar, já que não toca
# nenhuma dependência. Só o HEALTHCHECK do container dev usa /health/ready;
# o probe externo de produção que alimenta alertas continua em /health puro
# (ver comentário em app/api/health.py sobre por quê).
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
