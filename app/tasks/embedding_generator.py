"""Task de geração de embeddings em batch para legislação.

Processa artigos de legislação sem embedding, gerando vetores
384-dimensionais via SentenceTransformers e atualizando no banco.
Usado no seed inicial e atualização de legislação.
"""

import logging

logger = logging.getLogger("argus")


async def gerar_embeddings_batch_task(ctx: dict, batch_size: int = 50) -> dict:
    """Task arq para gerar embeddings de legislação em batch.

    Busca artigos de legislação sem embedding, gera em batch via
    SentenceTransformers e atualiza no banco. Processa em lotes
    para controlar uso de memória.

    Args:
        ctx: Contexto do worker arq com embedding_service e db_session_factory.
        batch_size: Tamanho do lote para processamento (padrão: 50).

    Returns:
        Dicionário com total de artigos processados.
    """
    from sqlalchemy import select

    from app.models.legislacao import Legislacao

    embedding_service = ctx["embedding_service"]
    db_factory = ctx["db_session_factory"]

    total_processados = 0

    async with db_factory() as db:
        try:
            # Buscar legislações sem embedding
            result = await db.execute(
                select(Legislacao).where(
                    Legislacao.ativo == True,  # noqa: E712
                    Legislacao.embedding.is_(None),
                )
            )
            legislacoes = result.scalars().all()

            if not legislacoes:
                logger.info("Nenhuma legislação pendente de embedding")
                return {"status": "sem_pendentes", "total": 0}

            logger.info(
                "Gerando embeddings para %d artigos de legislação",
                len(legislacoes),
            )

            # Processar em batches
            for i in range(0, len(legislacoes), batch_size):
                batch = legislacoes[i : i + batch_size]
                textos = [f"{leg.lei} Art. {leg.artigo}: {leg.texto}" for leg in batch]

                embeddings = embedding_service.gerar_embeddings_batch(textos)

                for leg, emb in zip(batch, embeddings):
                    leg.embedding = emb

                total_processados += len(batch)
                logger.info(
                    "Batch %d/%d concluído (%d artigos)",
                    (i // batch_size) + 1,
                    (len(legislacoes) + batch_size - 1) // batch_size,
                    len(batch),
                )

            await db.commit()

            logger.info("Embeddings gerados com sucesso: %d artigos", total_processados)
            return {"status": "sucesso", "total": total_processados}

        except Exception:
            await db.rollback()
            logger.exception("Erro ao gerar embeddings em batch")
            return {"status": "erro", "total": total_processados}
