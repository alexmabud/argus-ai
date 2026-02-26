"""Task de processamento de PDF para extração de texto e embedding.

Processa PDFs de boletins de ocorrência: download do S3, extração de
texto via PyMuPDF (fitz), chunking semântico e geração de embedding
vetorial para busca semântica via pgvector.
"""

import logging
from urllib.parse import urlparse

import fitz  # PyMuPDF

from app.services.storage_service import StorageService
from app.services.text_utils import chunk_text_semantico

logger = logging.getLogger("argus")


def extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de PDF usando PyMuPDF.

    Percorre todas as páginas do PDF e extrai texto com layout
    preservado. Páginas vazias são ignoradas.

    Args:
        pdf_bytes: Conteúdo do PDF em bytes.

    Returns:
        Texto extraído concatenado de todas as páginas.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    textos = []
    for page in doc:
        texto = page.get_text()
        if texto.strip():
            textos.append(texto.strip())
    doc.close()
    return "\n\n".join(textos)


def _extrair_key_da_url(url: str) -> str:
    """Extrai chave S3 a partir da URL do arquivo.

    Remove endpoint e bucket do caminho para obter apenas a key.

    Args:
        url: URL completa do arquivo no S3/R2.

    Returns:
        Chave (path) do arquivo no bucket.
    """
    parsed = urlparse(url)
    # URL: endpoint/bucket/key → path: /bucket/key
    parts = parsed.path.lstrip("/").split("/", 1)
    return parts[1] if len(parts) > 1 else parts[0]


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
    storage = StorageService()

    logger.info("Processando PDF da ocorrência %d", ocorrencia_id)

    async with db_factory() as db:
        try:
            # 1. Buscar ocorrência
            from sqlalchemy import select

            result = await db.execute(select(Ocorrencia).where(Ocorrencia.id == ocorrencia_id))
            ocorrencia = result.scalar_one_or_none()

            if ocorrencia is None:
                logger.error("Ocorrência %d não encontrada", ocorrencia_id)
                return {"status": "erro", "motivo": "Ocorrência não encontrada"}

            if ocorrencia.processada:
                logger.info("Ocorrência %d já processada, pulando", ocorrencia_id)
                return {"status": "já_processada"}

            # 2. Download PDF
            key = _extrair_key_da_url(ocorrencia.arquivo_pdf_url)
            pdf_bytes = await storage.download(key)

            # 3. Extrair texto
            texto = extrair_texto_pdf(pdf_bytes)
            if not texto.strip():
                logger.warning("PDF da ocorrência %d sem texto extraível", ocorrencia_id)
                ocorrencia.processada = True
                await db.commit()
                return {"status": "sem_texto"}

            # 4. Chunking semântico
            chunks = chunk_text_semantico(texto)

            # 5. Gerar embedding do texto completo
            embedding = embedding_service.gerar_embedding(texto[:5000])

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
            return {"status": "erro", "motivo": "Erro no processamento"}
