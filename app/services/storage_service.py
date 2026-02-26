"""Serviço de armazenamento de arquivos em S3/R2.

Gerencia upload, download e remoção de arquivos em storage S3-compatível
(Cloudflare R2 em produção, MinIO em desenvolvimento).
"""

import logging
import uuid

import aioboto3

from app.config import settings

logger = logging.getLogger("argus")


class StorageService:
    """Serviço de upload/download de arquivos para S3/R2.

    Gerencia operações assíncronas de armazenamento de arquivos usando
    aioboto3 para comunicação com storage S3-compatível.

    Attributes:
        _session: Sessão aioboto3 (lazy initialization).
    """

    def __init__(self):
        """Inicializa serviço de armazenamento."""
        self._session = aioboto3.Session()

    def _generate_key(self, prefix: str, filename: str) -> str:
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
            URL pública do arquivo no storage.

        Raises:
            Exception: Se falha no upload ao S3.
        """
        async with self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        ) as client:
            await client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )

        url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"
        logger.info("Upload concluído: %s", key)
        return url

    async def delete(self, key: str) -> None:
        """Remove arquivo do S3/R2.

        Args:
            key: Chave (caminho) do arquivo no bucket.

        Raises:
            Exception: Se falha na remoção do S3.
        """
        async with self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        ) as client:
            await client.delete_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
            )

        logger.info("Arquivo removido: %s", key)

    async def download(self, key: str) -> bytes:
        """Faz download de arquivo do S3/R2.

        Args:
            key: Chave (caminho) do arquivo no bucket.

        Returns:
            Conteúdo do arquivo em bytes.

        Raises:
            Exception: Se falha no download do S3.
        """
        async with self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        ) as client:
            response = await client.get_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
            )
            body = await response["Body"].read()

        logger.info("Download concluído: %s", key)
        return body
