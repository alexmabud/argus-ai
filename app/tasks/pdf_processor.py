"""Task de processamento de PDF para extração de texto e embedding.

Processa PDFs de boletins de ocorrência: download do S3, extração de
texto via PyMuPDF (fitz), chunking semântico e geração de embedding
vetorial para busca semântica via pgvector.
"""

import asyncio
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app.services.storage_service import StorageService
from app.services.text_utils import chunk_text_semantico
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")

#: Teto de páginas processadas por PDF — boletins de ocorrência reais têm
#: poucas páginas; um PDF hostil com contagem de páginas absurda (objetos
#: repetidos/aninhados, "PDF bomb") poderia travar o worker por muito tempo
#: mesmo dentro do limite de 50 MB de upload. Acima do teto, processa só as
#: primeiras N páginas e loga — não falha a ocorrência inteira por causa de
#: um documento anormalmente grande (achado #17/2026-07-13).
MAX_PDF_PAGES = 500


def extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de PDF usando PyMuPDF.

    Percorre as páginas do PDF (até MAX_PDF_PAGES) e extrai texto com
    layout preservado. Páginas vazias são ignoradas.

    Args:
        pdf_bytes: Conteúdo do PDF em bytes.

    Returns:
        Texto extraído concatenado das páginas processadas.

    Raises:
        RuntimeError: Se PyMuPDF não estiver instalado.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) não instalado — processamento de PDF indisponível")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_paginas = doc.page_count
    if total_paginas > MAX_PDF_PAGES:
        logger.warning(
            "PDF com %d páginas excede o teto de %d — processando só as primeiras %d",
            total_paginas,
            MAX_PDF_PAGES,
            MAX_PDF_PAGES,
        )
    textos = []
    for i in range(min(total_paginas, MAX_PDF_PAGES)):
        texto = doc[i].get_text()
        if texto.strip():
            textos.append(texto.strip())
    doc.close()
    return "\n\n".join(textos)


async def processar_pdf_task(ctx: dict, ocorrencia_id: int) -> dict:
    """Task arq para processar PDF de ocorrência.

    Pipeline completo:
    1. Busca ocorrência no banco
    2. Download PDF do S3/R2
    3. Extrai texto via PyMuPDF
    4. Chunking semântico do texto (seções do BO)
    5. Gera embedding do texto completo
    6. Atualiza ocorrência: texto_extraido, embedding, processada=True

    Args:
        ctx: Contexto do worker arq com embedding_service e db_session_factory.
        ocorrencia_id: ID da ocorrência para processar.

    Returns:
        Dicionário com status do processamento e metadados.
    """
    from app.models.ocorrencia import Ocorrencia

    embedding_service = ctx["embedding_service"]
    db_factory = ctx["db_session_factory"]
    storage = StorageService.get()

    logger.info("Processando PDF da ocorrência %d", ocorrencia_id)

    async with db_factory() as db:
        try:
            # 1. Buscar ocorrência (só ativa — achado #21/2026-07-13: mesma
            # defesa do face_processor contra job enfileirado antes de um
            # soft delete reprocessar um registro já apagado).
            from sqlalchemy import select

            result = await db.execute(
                select(Ocorrencia)
                .where(Ocorrencia.id == ocorrencia_id, Ocorrencia.ativo.is_(True))
                .with_for_update(skip_locked=True)
            )
            ocorrencia = result.scalar_one_or_none()

            if ocorrencia is None:
                logger.info("Ocorrência %d não encontrada ou inativa, pulando", ocorrencia_id)
                return {"status": "erro", "motivo": "Ocorrência não encontrada ou inativa"}

            if ocorrencia.processada:
                logger.info("Ocorrência %d já processada, pulando", ocorrencia_id)
                return {"status": "já_processada"}

            # 2. Download PDF
            key = extrair_key_da_url(ocorrencia.arquivo_pdf_url)
            pdf_bytes = await storage.download(key)

            # 3. Extrair texto (CPU-bound → thread pool)
            texto = await asyncio.to_thread(extrair_texto_pdf, pdf_bytes)
            if not texto.strip():
                logger.warning("PDF da ocorrência %d sem texto extraível", ocorrencia_id)
                ocorrencia.processada = True
                await db.commit()
                return {"status": "sem_texto"}

            # 4. Chunking semântico (CPU-bound → thread pool)
            chunks = await asyncio.to_thread(chunk_text_semantico, texto)

            # 5. Gerar embedding do texto completo (CPU-bound → thread pool)
            embedding = await asyncio.to_thread(embedding_service.gerar_embedding, texto[:5000])

            # 6. Atualizar ocorrência
            ocorrencia.texto_extraido = texto
            ocorrencia.embedding = embedding
            ocorrencia.processada = True
            await db.commit()

            logger.info(
                "Ocorrência %d processada: %d chars, %d chunks",
                ocorrencia_id,
                len(texto),
                len(chunks),
            )
            return {
                "status": "sucesso",
                "caracteres": len(texto),
                "chunks": len(chunks),
            }

        except Exception:
            await db.rollback()
            logger.exception("Erro ao processar PDF da ocorrência %d", ocorrencia_id)
            # Relança para o arq reprocessar (max_tries) em vez de mascarar como
            # sucesso — senão a ocorrência fica sem texto/embedding (#9 auditoria).
            raise
