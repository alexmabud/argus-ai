"""Task de processamento facial para geração de embedding InsightFace.

Processa fotos enviadas: download do S3, extração de embedding facial
de 512 dimensões via InsightFace e atualização no banco para busca
por similaridade via pgvector.
"""

import logging
from urllib.parse import urlparse

from app.services.storage_service import StorageService

logger = logging.getLogger("argus")


def _extrair_key_da_url(url: str) -> str:
    """Extrai chave S3 a partir da URL do arquivo.

    Args:
        url: URL completa do arquivo no S3/R2.

    Returns:
        Chave (path) do arquivo no bucket.
    """
    parsed = urlparse(url)
    parts = parsed.path.lstrip("/").split("/", 1)
    return parts[1] if len(parts) > 1 else parts[0]


async def processar_face_task(ctx: dict, foto_id: int) -> dict:
    """Task arq para processar embedding facial de uma foto.

    Pipeline:
    1. Busca foto no banco
    2. Skip se face_processada=True
    3. Download imagem do S3/R2
    4. Extrai embedding facial via InsightFace (512-dim)
    5. Atualiza foto: embedding_face, face_processada=True

    Args:
        ctx: Contexto do worker arq com face_service e db_session_factory.
        foto_id: ID da foto para processar.

    Returns:
        Dicionário com status do processamento.
    """
    from sqlalchemy import select

    from app.models.foto import Foto

    face_service = ctx.get("face_service")
    if face_service is None:
        logger.warning("FaceService indisponível, pulando foto %d", foto_id)
        return {"status": "indisponível", "motivo": "FaceService não carregado"}

    db_factory = ctx["db_session_factory"]
    storage = StorageService()

    logger.info("Processando face da foto %d", foto_id)

    async with db_factory() as db:
        try:
            # 1. Buscar foto
            result = await db.execute(
                select(Foto).where(Foto.id == foto_id).with_for_update(skip_locked=True)
            )
            foto = result.scalar_one_or_none()

            if foto is None:
                logger.error("Foto %d não encontrada", foto_id)
                return {"status": "erro", "motivo": "Foto não encontrada"}

            if foto.face_processada:
                logger.info("Foto %d já processada, pulando", foto_id)
                return {"status": "já_processada"}

            # 2. Download imagem
            key = _extrair_key_da_url(foto.arquivo_url)
            image_bytes = await storage.download(key)

            # 3. Extrair embedding facial
            embedding = face_service.extrair_embedding(image_bytes)

            if embedding is None:
                logger.info("Nenhum rosto detectado na foto %d", foto_id)
                foto.face_processada = True
                await db.commit()
                return {"status": "sem_rosto"}

            # 4. Atualizar foto
            foto.embedding_face = embedding
            foto.face_processada = True
            await db.commit()

            logger.info("Face processada com sucesso para foto %d", foto_id)
            return {"status": "sucesso"}

        except Exception:
            await db.rollback()
            logger.exception("Erro ao processar face da foto %d", foto_id)
            return {"status": "erro", "motivo": "Erro no processamento"}
