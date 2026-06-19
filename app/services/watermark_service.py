"""Serviço da camada 2 do watermark rastreável: marca queimada com cache.

Orquestra a geração e o cache da variante marcada de cada imagem por
``(asset, matrícula)``. O cache vive no próprio MinIO sob o prefixo
``wm/v1/`` — escolhido em vez do Redis porque o Redis de produção é
compartilhado (256MB, allkeys-lru) com a fila arq, rate-limit e
login-guard, e blobs de imagem despejariam infra crítica.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from botocore.exceptions import ClientError
from PIL import UnidentifiedImageError

from app.services.storage_service import StorageService
from app.utils.imaging import burn_watermark

#: Prefixo versionado do cache. Bump (v2, ...) invalida tudo se o estilo mudar.
WM_PREFIX = "wm/v1"

#: Content-types tratados como imagem direta (fast-path de marcação).
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

#: Content-types ambíguos: precisam de sniff (podem ser imagem mal-rotulada).
AMBIGUOUS_CONTENT_TYPES = {"application/octet-stream", "binary/octet-stream", ""}


@dataclass(frozen=True)
class WatermarkResult:
    """Resultado da marcação.

    Attributes:
        body: Bytes a servir (marcados se imagem; originais se passthrough).
        content_type: Content-type a devolver ao cliente.
        is_image: True se foi marcado; False se passou sem marca.
    """

    body: bytes
    content_type: str
    is_image: bool


class WatermarkService:
    """Gera/recupera a variante marcada de uma imagem por (asset, matrícula)."""

    @staticmethod
    def cache_key(matricula: str, original_key: str) -> str:
        """Calcula a key de cache no MinIO para o par (matrícula, asset).

        Args:
            matricula: Matrícula do usuário.
            original_key: Key original do objeto no bucket.

        Returns:
            Key no formato ``wm/v1/{hash16(matricula)}/{original_key}``.
        """
        h = hashlib.sha256(matricula.encode()).hexdigest()[:16]
        return f"{WM_PREFIX}/{h}/{original_key}"

    @staticmethod
    def deve_tentar_marcar(content_type: str | None) -> bool:
        """Indica se vale tentar marcar (imagem conhecida ou ambígua).

        PDFs e vídeos conhecidos retornam False e seguem o streaming normal,
        sem baixar bytes à toa.

        Args:
            content_type: Content-type informado pelo storage.

        Returns:
            True para tipos de imagem ou ambíguos; False caso contrário.
        """
        ct = (content_type or "").lower()
        return ct in IMAGE_CONTENT_TYPES or ct in AMBIGUOUS_CONTENT_TYPES

    async def get_or_create(
        self, original_key: str, matricula: str, content_type: str | None
    ) -> WatermarkResult:
        """Devolve a variante marcada (cache ou geração) ou passthrough.

        Fluxo: tenta o cache; em miss, baixa o original, faz sniff via
        ``burn_watermark`` (UnidentifiedImageError => passthrough), e em
        sucesso faz upload da variante. Erro de render em imagem confirmada
        propaga (fail-closed escopado → 500 no proxy).

        Args:
            original_key: Key do objeto original no bucket.
            matricula: Matrícula do usuário autenticado.
            content_type: Content-type informado pelo storage.

        Returns:
            WatermarkResult com bytes, content-type e flag is_image.

        Raises:
            Exception: Qualquer erro de render numa imagem confirmada
                (fail-closed). NoSuchKey do original propaga como 404 no proxy.
        """
        storage = StorageService.get()
        ckey = self.cache_key(matricula, original_key)

        # 1) cache hit?
        try:
            body, ct = await storage.download_with_meta(ckey)
            return WatermarkResult(body=body, content_type=ct, is_image=True)
        except ClientError as exc:
            miss_codes = {"NoSuchKey", "404", "NoSuchBucket"}
            if exc.response.get("Error", {}).get("Code") not in miss_codes:
                raise

        # 2) miss → baixa original e tenta marcar
        original, orig_ct = await storage.download_with_meta(original_key)
        try:
            marcada = await asyncio.to_thread(burn_watermark, original, matricula)
        except UnidentifiedImageError:
            # Não era imagem (ex.: octet-stream que era PDF) → passthrough.
            return WatermarkResult(body=original, content_type=orig_ct, is_image=False)

        out_ct = orig_ct if (orig_ct or "").lower() in IMAGE_CONTENT_TYPES else "image/jpeg"
        await storage.upload(marcada, ckey, content_type=out_ct)
        return WatermarkResult(body=marcada, content_type=out_ct, is_image=True)
