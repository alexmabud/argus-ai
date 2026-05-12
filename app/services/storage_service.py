"""Serviço de armazenamento de arquivos em S3/R2.

Gerencia upload, download e remoção de arquivos em storage S3-compatível
(Cloudflare R2 em produção, MinIO em desenvolvimento). URLs geradas são
sempre relativas (/storage/...) para evitar mixed-content em HTTPS.

O cliente S3 é mantido como singleton inicializado no lifespan da
aplicação/worker para reaproveitar TCP/TLS keep-alive entre requests,
evitando o custo de handshake (100-300ms) a cada operação contra R2.
"""

import logging
import re
import uuid
from typing import Any

import aioboto3

from app.config import settings

logger = logging.getLogger("argus")

#: Regex para extrair chave relativa de URLs absolutas legadas do storage.
#: Captura o path a partir do nome do bucket (ex: "argus/fotos/img.jpg").
_ABSOLUTE_URL_RE = re.compile(r"https?://[^/]+/(" + re.escape(settings.S3_BUCKET) + r"/.+)$")


def normalize_storage_url(url: str | None) -> str | None:
    """Converte URL de storage absoluta legada para path relativo.

    URLs novas já são relativas (/storage/bucket/key). URLs antigas
    armazenadas como http://host:port/bucket/key são convertidas para
    o formato relativo, eliminando erros de mixed-content em HTTPS.

    Args:
        url: URL do arquivo no storage (absoluta ou relativa) ou None.

    Returns:
        Path relativo (/storage/bucket/key) ou None se entrada for None.
    """
    if url is None:
        return None
    if url.startswith("/storage/"):
        return url
    match = _ABSOLUTE_URL_RE.match(url)
    if match:
        return f"/storage/{match.group(1)}"
    return url


class StorageService:
    """Serviço S3/R2 com cliente persistente (reusa TCP keep-alive).

    O cliente é criado em ``startup()`` (lifespan da API ou worker) e
    fechado em ``shutdown()``. As operações usam ``self._client``
    diretamente, evitando o handshake TCP/TLS/SigV4 por chamada que o
    padrão anterior (``async with session.client(...)``) impunha.

    Use ``StorageService.get()`` para obter a instância singleton
    compartilhada pelo processo.

    Attributes:
        _session: Sessão aioboto3 usada para criar o cliente persistente.
        _client_ctx: Context manager do cliente (mantido para fechamento).
        _client: Cliente S3 aberto, pronto para uso após ``startup()``.
    """

    _instance: "StorageService | None" = None

    def __init__(self) -> None:
        """Inicializa o serviço sem abrir conexões — chame ``startup()``."""
        self._session = aioboto3.Session()
        self._client_ctx: Any = None
        self._client: Any = None

    @classmethod
    def get(cls) -> "StorageService":
        """Retorna a instância singleton (criada sob demanda).

        A instância é compartilhada por todo o processo. ``startup()`` e
        ``shutdown()`` são chamados pelo lifespan da API e do worker.

        Returns:
            Instância única de ``StorageService``.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def startup(self) -> None:
        """Abre o cliente S3 persistente.

        Idempotente — chamar mais de uma vez é seguro (apenas o primeiro
        ``startup`` abre o cliente). Deve ser chamado no lifespan da
        aplicação FastAPI e no ``on_startup`` do worker arq.
        """
        if self._client is not None:
            return
        self._client_ctx = self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self._client = await self._client_ctx.__aenter__()

    async def shutdown(self) -> None:
        """Fecha o cliente S3 aberto via ``startup()``.

        Idempotente. Deve ser chamado no encerramento do lifespan da
        aplicação FastAPI e no ``on_shutdown`` do worker arq.
        """
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client_ctx = None
            self._client = None

    def _ensure_client(self) -> Any:
        """Retorna o cliente S3, exigindo que ``startup()`` já tenha rodado.

        Returns:
            Cliente S3 aberto pelo ``startup()``.

        Raises:
            RuntimeError: Se ``startup()`` não foi chamado antes.
        """
        if self._client is None:
            raise RuntimeError(
                "StorageService não inicializado — chame startup() no lifespan."
            )
        return self._client

    def generate_key(self, prefix: str, filename: str) -> str:
        """Gera chave única para armazenamento no S3.

        Args:
            prefix: Prefixo do caminho (ex: "fotos", "pdfs").
            filename: Nome original do arquivo.

        Returns:
            Chave única no formato "{prefix}/{uuid}_{filename}".
        """
        unique_id = uuid.uuid4().hex[:12]
        return f"{prefix}/{unique_id}_{filename}"

    async def upload(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Faz upload de arquivo para S3/R2.

        Args:
            file_bytes: Conteúdo do arquivo em bytes.
            key: Chave (caminho) no bucket S3.
            content_type: MIME type do arquivo (padrão: image/jpeg).

        Returns:
            URL relativa do arquivo no storage (/storage/bucket/key).

        Raises:
            RuntimeError: Se ``startup()`` não foi chamado antes.
            Exception: Se falha no upload ao S3.
        """
        client = self._ensure_client()
        await client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info("Upload concluído: %s", key)
        return f"/storage/{settings.S3_BUCKET}/{key}"

    async def delete(self, key: str) -> None:
        """Remove arquivo do S3/R2.

        Args:
            key: Chave (caminho) do arquivo no bucket.

        Raises:
            RuntimeError: Se ``startup()`` não foi chamado antes.
            Exception: Se falha na remoção do S3.
        """
        client = self._ensure_client()
        await client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
        logger.info("Arquivo removido: %s", key)

    async def download(self, key: str) -> bytes:
        """Faz download de arquivo do S3/R2.

        Args:
            key: Chave (caminho) do arquivo no bucket.

        Returns:
            Conteúdo do arquivo em bytes.

        Raises:
            RuntimeError: Se ``startup()`` não foi chamado antes.
            Exception: Se falha no download do S3.
        """
        body, _ = await self.download_with_meta(key)
        return body

    async def download_with_meta(self, key: str) -> tuple[bytes, str]:
        """Faz download retornando bytes e content type informado pelo S3.

        Usado pelo proxy /storage/* para devolver o arquivo com o mesmo
        Content-Type registrado no upload, sem precisar adivinhar pela
        extensão.

        Args:
            key: Chave (caminho) do arquivo no bucket.

        Returns:
            Tupla ``(bytes, content_type)``. ``content_type`` é o valor
            retornado pelo S3 ou ``application/octet-stream`` como fallback.

        Raises:
            RuntimeError: Se ``startup()`` não foi chamado antes.
            botocore.exceptions.ClientError: Se a chave não existe (NoSuchKey)
                ou outro erro de S3 (acesso, bucket inválido, etc).
        """
        client = self._ensure_client()
        response = await client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        body = await response["Body"].read()
        content_type = response.get("ContentType") or "application/octet-stream"
        return body, content_type
