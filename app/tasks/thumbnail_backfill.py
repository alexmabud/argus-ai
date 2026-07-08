"""Task arq para backfill de thumbnails em fotos legadas.

Gera ``thumbnail_url`` para fotos cadastradas antes da introdução do
campo. Skip se a foto já tem thumb, é soft-deleted ou não é imagem.
Idempotente: re-execuções na mesma foto são seguras.
"""

import asyncio
import logging

from sqlalchemy import select

from app.models.foto import Foto
from app.services.foto_service import FotoService
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
        5. Atualiza ``foto.thumbnail_url``, recalcula a foto de perfil da
           pessoa se for a foto de rosto ativa mais recente, e comita.

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
            # skip_locked: dois workers que tentem o mesmo foto_id simultaneamente
            # — outro pega lock, este recebe None e retorna como "pulado_inexistente".
            # Evita gerar/uplodar thumb duplicado quando o C2 enfileira em massa.
            result = await db.execute(
                select(Foto)
                .where(Foto.id == foto_id, Foto.ativo.is_(True))
                .with_for_update(skip_locked=True)
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

            # Se essa foto é a foto de rosto ativa mais recente da pessoa,
            # o backfill do thumb precisa refletir em foto_principal_thumb_url
            # — senão o perfil fica com thumb desatualizado indefinidamente.
            if foto.tipo == "rosto" and foto.pessoa_id is not None:
                await FotoService(db).recomputar_foto_principal(foto.pessoa_id)

            await db.commit()
            logger.info("Thumb backfilled para foto %d", foto_id)
            return {"status": "sucesso"}

        except Exception:
            # Nada vaza para o worker — uma foto problemática não deve estourar
            # max_tries do arq nem bloquear o pool. logger.exception preserva o
            # tipo do erro no traceback.
            await db.rollback()
            logger.exception("Erro no backfill da foto %d", foto_id)
            return {"status": "erro"}
