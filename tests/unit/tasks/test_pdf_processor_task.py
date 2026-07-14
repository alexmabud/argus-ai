"""Teste da task arq de processamento de PDF (nível de orquestração).

Complementa tests/unit/test_pdf_processor.py (que só cobre os helpers
extrair_texto_pdf/extrair_key_da_url) com o comportamento de
processar_pdf_task diante de ocorrência inexistente/inativa.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tasks.pdf_processor import processar_pdf_task


def _ctx_with_db(ocorrencia: MagicMock | None) -> dict:
    """Constrói ctx do arq com factory de session retornando a ocorrência dada."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = ocorrencia
    db.execute = AsyncMock(return_value=result)

    db_cm = AsyncMock()
    db_cm.__aenter__ = AsyncMock(return_value=db)
    db_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=db_cm)

    return {"db_session_factory": factory, "embedding_service": MagicMock(), "_db": db}


@pytest.mark.asyncio
async def test_processar_pdf_pula_ocorrencia_inexistente_ou_inativa():
    """Ocorrência inexistente OU soft-deleted (ativo=False) não é processada.

    Achado #21/2026-07-13: mesma defesa aplicada ao face_processor — a
    query já filtra ativo=True, então um job enfileirado antes de um
    eventual soft delete futuro de Ocorrencia não reprocessa o registro.
    """
    ctx = _ctx_with_db(None)
    result = await processar_pdf_task(ctx, 999)
    assert result["status"] == "erro"
    ctx["embedding_service"].gerar_embedding.assert_not_called()
