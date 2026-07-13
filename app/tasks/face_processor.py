"""Task de processamento facial para geração de embedding InsightFace.

Processa fotos enviadas: download do S3, extração de embedding facial
de 512 dimensões via InsightFace e atualização no banco para busca
por similaridade via pgvector.

Nota de segurança (achado #21/2026-07-13): a task recebe apenas ``foto_id``,
sem contexto de usuário/sessão — jobs de background não têm "quem pediu"
para revalidar. A revalidação possível aqui é no dado (``ativo=True``, já
implementada abaixo), não em autorização de usuário. Quem efetivamente
impede um `foto_id` arbitrário/de outro escopo ser enfileirado é a rede e a
credencial do Redis (só a API deve conseguir publicar nesta fila) — Redis
continua trust boundary de infra; esta revalidação no worker é mitigação em
profundidade (evita reprocessar registro apagado), não substitui isolar a
rede do Redis.
"""

import asyncio
import logging

from app.services.storage_service import StorageService
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")


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
    storage = StorageService.get()

    logger.info("Processando face da foto %d", foto_id)

    async with db_factory() as db:
        try:
            # 1. Buscar foto (só ativa — achado #21/2026-07-13: sem o filtro,
            # um job enfileirado antes de um soft delete reprocessava e
            # repopulava embedding_face de uma foto já apagada, desfazendo
            # silenciosamente o soft delete/direito de eliminação).
            result = await db.execute(
                select(Foto)
                .where(Foto.id == foto_id, Foto.ativo.is_(True))
                .with_for_update(skip_locked=True)
            )
            foto = result.scalar_one_or_none()

            if foto is None:
                logger.info("Foto %d não encontrada ou inativa, pulando", foto_id)
                return {"status": "erro", "motivo": "Foto não encontrada ou inativa"}

            if foto.face_processada:
                logger.info("Foto %d já processada, pulando", foto_id)
                return {"status": "já_processada"}

            # 2. Download imagem
            key = extrair_key_da_url(foto.arquivo_url)
            image_bytes = await storage.download(key)

            # 3. Extrair embedding facial (CPU-bound → thread pool)
            embedding = await asyncio.to_thread(face_service.extrair_embedding, image_bytes)

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
            # Relança para o arq reprocessar (max_tries) em vez de mascarar como
            # sucesso — senão a foto fica presa em face_processada=False (#9 auditoria).
            raise
