"""Testes da task arq de backfill de thumbnails."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.thumbnail_backfill import gerar_thumbnail_backfill_task


def _foto_mock(
    *,
    foto_id: int = 1,
    arquivo_url: str = "/storage/argus/fotos/abc_x.jpg",
    thumbnail_url: str | None = None,
    ativo: bool = True,
) -> MagicMock:
    """Cria mock de Foto com campos relevantes para a task."""
    foto = MagicMock()
    foto.id = foto_id
    foto.arquivo_url = arquivo_url
    foto.thumbnail_url = thumbnail_url
    foto.ativo = ativo
    return foto


def _ctx_with_db(foto: MagicMock | None) -> dict:
    """Constrói ctx do arq com factory de session retornando a foto dada."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = foto
    db.execute = AsyncMock(return_value=result)

    db_cm = AsyncMock()
    db_cm.__aenter__ = AsyncMock(return_value=db)
    db_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=db_cm)

    storage = MagicMock()
    storage.download = AsyncMock(return_value=b"image-bytes")
    storage.upload = AsyncMock(return_value="/storage/argus/thumbs/abc_x_thumb.jpg")
    storage.generate_key = MagicMock(return_value="thumbs/xxx_x_thumb.jpg")

    return {"db_session_factory": factory, "storage": storage, "_db": db}


@pytest.mark.asyncio
async def test_backfill_pula_foto_com_thumb_existente():
    """Foto que já tem thumbnail_url deve ser pulada sem download."""
    foto = _foto_mock(thumbnail_url="/storage/argus/thumbs/already.jpg")
    ctx = _ctx_with_db(foto)
    result = await gerar_thumbnail_backfill_task(ctx, foto.id)
    assert result["status"] == "já_processada"
    ctx["storage"].download.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_pula_foto_inexistente():
    """Foto inexistente (ou soft-deleted) retorna status pulado_inexistente."""
    ctx = _ctx_with_db(None)
    result = await gerar_thumbnail_backfill_task(ctx, 999)
    assert result["status"] == "pulado_inexistente"


@pytest.mark.asyncio
async def test_backfill_pula_pdf():
    """Arquivo não-imagem (ex: PDF) deve ser pulado."""
    foto = _foto_mock(arquivo_url="/storage/argus/midias/auto.pdf")
    ctx = _ctx_with_db(foto)
    result = await gerar_thumbnail_backfill_task(ctx, foto.id)
    assert result["status"] == "pulado_nao_imagem"
    ctx["storage"].download.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_gera_thumb_e_atualiza_foto():
    """Caminho feliz: gera thumb, faz upload e atualiza thumbnail_url."""
    foto = _foto_mock(arquivo_url="/storage/argus/fotos/abc_x.jpg")
    ctx = _ctx_with_db(foto)

    with patch(
        "app.tasks.thumbnail_backfill.gerar_thumbnail",
        return_value=b"thumb-bytes",
    ):
        result = await gerar_thumbnail_backfill_task(ctx, foto.id)

    assert result["status"] == "sucesso"
    assert foto.thumbnail_url == "/storage/argus/thumbs/abc_x_thumb.jpg"
    ctx["_db"].commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_falha_loga_e_retorna_erro():
    """Falha no download/processamento não propaga — rollback + erro."""
    foto = _foto_mock(arquivo_url="/storage/argus/fotos/abc_x.jpg")
    ctx = _ctx_with_db(foto)
    ctx["storage"].download = AsyncMock(side_effect=RuntimeError("S3 fora"))

    result = await gerar_thumbnail_backfill_task(ctx, foto.id)
    assert result["status"] == "erro"
    ctx["_db"].rollback.assert_awaited_once()
