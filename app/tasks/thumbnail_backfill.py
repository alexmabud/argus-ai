"""Task arq para backfill de thumbnails em fotos legadas.

Gera ``thumbnail_url`` para fotos cadastradas antes da introdução do
campo. Skip se a foto já tem thumb, é soft-deleted ou não é imagem.
Idempotente: re-execuções na mesma foto são seguras.
"""

import asyncio
import logging

from botocore.exceptions import BotoCoreError, ClientError
from PIL import UnidentifiedImageError
from sqlalchemy import select

from app.models.foto import Foto
from app.services.storage_service import StorageService
from app.utils.imaging import gerar_thumbnail
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")

#: Extensões consideradas imagens elegíveis para thumbnail.
_EXTENSOES_IMAGEM = (".jpg", ".jpeg", ".png", ".webp")


async def gerar_thumbnail_backfill_task(ctx: dict, foto_id: int) -> dict:
    """Gera thumbnail de uma foto legada e atualiza ``thumbnail_url``.

    Pipeline:
        1. Carrega ``Foto`` (com ``ativo=True``).
        2. Skip se a foto não existe, já tem thumb ou não é imagem.
        3. Baixa bytes da imagem original do storage.
        4. Gera thumbnail (CPU-bound em thread) e faz upload em ``thumbs/``.
        5. Atualiza ``foto.thumbnail_url`` e comita.

    Args:
        ctx: Contexto do worker arq. Espera ``db_session_factory`` e
            opcionalmente ``storage`` (cai em ``StorageService.get()`` se
            ausente).
        foto_id: ID da foto a processar.

    Returns:
        Dicionário com chave ``status`` em
        {"sucesso", "já_processada", "pulado_nao_imagem",
        "pulado_inexistente", "erro"}.
    """
    db_factory = ctx["db_session_factory"]
    storage: StorageService = ctx.get("storage") or StorageService.get()

    async with db_factory() as db:
        try:
            result = await db.execute(
                select(Foto).where(
                    Foto.id == foto_id,
                    Foto.ativo == True,  # noqa: E712
                )
            )
            foto = result.scalar_one_or_none()
            if foto is None:
                return {"status": "pulado_inexistente"}
            if foto.thumbnail_url:
                return {"status": "já_processada"}

            url_lower = foto.arquivo_url.lower()
            if not any(url_lower.endswith(ext) for ext in _EXTENSOES_IMAGEM):
                return {"status": "pulado_nao_imagem"}

            key = extrair_key_da_url(foto.arquivo_url)
            image_bytes = await storage.download(key)
            thumb_bytes = await asyncio.to_thread(gerar_thumbnail, image_bytes)

            filename = key.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "_thumb.jpg"
            thumb_key = storage.generate_key("thumbs", filename)
            thumb_url = await storage.upload(
                thumb_bytes,
                thumb_key,
                content_type="image/jpeg",
            )

            foto.thumbnail_url = thumb_url
            await db.commit()
            logger.info("Thumb backfilled para foto %d", foto_id)
            return {"status": "sucesso"}

        except (UnidentifiedImageError, OSError, ClientError, BotoCoreError):
            await db.rollback()
            logger.exception("Erro no backfill da foto %d", foto_id)
            return {"status": "erro"}
        except Exception:
            # Garantia: nenhum erro inesperado vaza para o worker (degradação graceful).
            await db.rollback()
            logger.exception("Erro inesperado no backfill da foto %d", foto_id)
            return {"status": "erro"}
