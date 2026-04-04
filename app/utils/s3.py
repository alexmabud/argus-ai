"""Utilitários para manipulação de URLs S3/R2.

Funções auxiliares para extrair chaves de objetos a partir de URLs
de storage, suportando formatos de endpoint direto e proxy reverso.
"""

from urllib.parse import urlparse


def extrair_key_da_url(url: str) -> str:
    """Extrai chave S3 a partir da URL do arquivo.

    Suporta URLs nos formatos:
    - ``/storage/{bucket}/{key}`` (proxy reverso com prefixo relativo)
    - ``http://minio:9000/{bucket}/{key}`` (endpoint direto)
    - ``https://dominio.com/storage/{bucket}/{key}`` (proxy reverso absoluto)

    A key é extraída localizando o nome do bucket no path e retornando
    tudo que vem depois dele.

    Args:
        url: URL completa ou relativa do arquivo no S3/R2.

    Returns:
        Chave (path) do arquivo no bucket, sem o nome do bucket.
    """
    from app.config import settings

    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    marker = f"{settings.S3_BUCKET}/"
    idx = path.find(marker)
    if idx >= 0:
        return path[idx + len(marker) :]
    # Fallback: remove primeiro segmento do path
    parts = path.split("/", 1)
    return parts[1] if len(parts) > 1 else parts[0]
