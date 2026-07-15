"""Testes de regressão para o startup do worker arq.

Achado 2026-07-15 (investigação do alerta ``alert-worker-parado``): o worker
nunca chamava ``setup_logging()`` — só a API fazia isso no lifespan
(``app/main.py``). Resultado: todo ``logger.info`` do worker (inclusive das
tasks de processamento de foto/PDF) era descartado silenciosamente, porque o
root logger sem configuração fica em WARNING por padrão — deixando o worker
sem visibilidade operacional para diagnosticar incidentes.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app import worker


@pytest.mark.asyncio
async def test_startup_configura_logging():
    """startup() deve chamar setup_logging() antes de carregar os serviços.

    Sem isso, logs INFO do worker (startup, progresso de jobs) são
    descartados silenciosamente — só exceções/warnings vazam sem formatação
    via ``logging.lastResort``, cegando o diagnóstico de incidentes.
    """
    ctx: dict = {}
    with (
        patch.object(worker, "setup_logging") as mock_setup_logging,
        patch("app.services.embedding_service.EmbeddingService"),
        patch("app.services.face_service.FaceService"),
        patch("app.services.storage_service.StorageService.get") as mock_storage_get,
    ):
        mock_storage_get.return_value.startup = AsyncMock()
        await worker.startup(ctx)

    mock_setup_logging.assert_called_once()
