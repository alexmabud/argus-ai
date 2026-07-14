"""Testes da task arq de processamento de embedding facial."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.face_processor import processar_face_task


def _foto_mock(
    *,
    foto_id: int = 1,
    arquivo_url: str = "/storage/argus/fotos/abc_x.jpg",
    face_processada: bool = False,
) -> MagicMock:
    """Cria mock de Foto com campos relevantes para a task."""
    foto = MagicMock()
    foto.id = foto_id
    foto.arquivo_url = arquivo_url
    foto.face_processada = face_processada
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

    face_service = MagicMock()
    face_service.extrair_embedding = MagicMock(return_value=[0.1] * 512)

    return {
        "db_session_factory": factory,
        "face_service": face_service,
        "_db": db,
        "_face_service": face_service,
    }


@pytest.mark.asyncio
async def test_processar_face_pula_foto_inexistente_ou_inativa():
    """Foto inexistente OU soft-deleted (ativo=False) não é processada.

    Achado #21/2026-07-13: sem o filtro ativo=True na query, um job
    enfileirado antes de um soft delete reprocessava a foto e repopulava
    embedding_face, desfazendo silenciosamente o direito de eliminação
    (issue #02) sempre que a foto fosse apagada entre o enqueue e a
    execução do worker.
    """
    ctx = _ctx_with_db(None)
    result = await processar_face_task(ctx, 999)
    assert result["status"] == "erro"
    ctx["_face_service"].extrair_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_processar_face_pula_ja_processada():
    """Foto com face_processada=True é pulada sem reprocessar."""
    foto = _foto_mock(face_processada=True)
    ctx = _ctx_with_db(foto)
    result = await processar_face_task(ctx, foto.id)
    assert result["status"] == "já_processada"


@pytest.mark.asyncio
async def test_processar_face_sem_face_service_retorna_indisponivel():
    """FaceService não carregado (ex: insightface ausente) retorna status claro."""
    ctx = _ctx_with_db(_foto_mock())
    ctx["face_service"] = None
    result = await processar_face_task(ctx, 1)
    assert result["status"] == "indisponível"


@pytest.mark.asyncio
async def test_processar_face_com_sucesso_atualiza_embedding():
    """Caminho feliz: extrai embedding e marca face_processada=True."""
    foto = _foto_mock()
    ctx = _ctx_with_db(foto)

    with patch("app.tasks.face_processor.StorageService") as mock_storage_cls:
        mock_storage = MagicMock()
        mock_storage.download = AsyncMock(return_value=b"image-bytes")
        mock_storage_cls.get.return_value = mock_storage

        result = await processar_face_task(ctx, foto.id)

    assert result["status"] == "sucesso"
    assert foto.embedding_face == [0.1] * 512
    assert foto.face_processada is True
    ctx["_db"].commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_processar_face_sem_rosto_detectado_marca_processada():
    """Nenhum rosto detectado ainda marca face_processada=True (não fica em loop)."""
    foto = _foto_mock()
    ctx = _ctx_with_db(foto)
    ctx["face_service"].extrair_embedding = MagicMock(return_value=None)

    with patch("app.tasks.face_processor.StorageService") as mock_storage_cls:
        mock_storage = MagicMock()
        mock_storage.download = AsyncMock(return_value=b"image-bytes")
        mock_storage_cls.get.return_value = mock_storage

        result = await processar_face_task(ctx, foto.id)

    assert result["status"] == "sem_rosto"
    assert foto.face_processada is True
