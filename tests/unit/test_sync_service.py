"""Testes unitários para o serviço de sincronização offline.

Valida processamento de batch, deduplicação por client_id,
tratamento de tipos desconhecidos e erro individual.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.sync import SyncItem
from app.services.sync_service import SyncService


class TestProcessBatch:
    """Testes para SyncService.process_batch()."""

    @pytest.fixture
    def service(self):
        """Cria instância de SyncService com session mock."""
        db = AsyncMock()
        return SyncService(db)

    @pytest.fixture
    def mock_user(self):
        """Cria mock de usuário autenticado."""
        user = MagicMock()
        user.id = 1
        user.guarnicao_id = 1
        return user

    async def test_tipo_desconhecido_retorna_error(self, service, mock_user):
        """Deve retornar erro para tipo desconhecido."""
        items = [
            SyncItem(
                client_id="uuid-1",
                tipo="invalido",
                dados={"foo": "bar"},
            )
        ]

        results = await service.process_batch(items, mock_user)

        assert len(results) == 1
        assert results[0].status == "error"
        assert "desconhecido" in results[0].error.lower()

    @patch("app.services.sync_service.AbordagemService")
    async def test_abordagem_sync_ok(self, mock_abd_cls, service, mock_user):
        """Deve sincronizar abordagem com sucesso."""
        # Mock deduplicação — não encontra existente
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.commit = AsyncMock()

        mock_abd = AsyncMock()
        mock_abd_cls.return_value = mock_abd

        items = [
            SyncItem(
                client_id="uuid-abd",
                tipo="abordagem",
                dados={
                    "data_hora": "2026-01-01T10:00:00",
                    "latitude": -22.9,
                    "longitude": -43.1,
                    "observacao": "Teste offline",
                    "pessoa_ids": [],
                    "veiculo_ids": [],
                },
            )
        ]

        results = await service.process_batch(items, mock_user)

        assert len(results) == 1
        assert results[0].status == "ok"

    async def test_deduplicacao_client_id(self, service, mock_user):
        """Deve retornar ok sem recriar se client_id já existe."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42  # já existe
        service.db.execute = AsyncMock(return_value=mock_result)

        items = [
            SyncItem(
                client_id="uuid-dup",
                tipo="abordagem",
                dados={"data_hora": "2026-01-01T10:00:00"},
            )
        ]

        results = await service.process_batch(items, mock_user)

        assert len(results) == 1
        assert results[0].status == "ok"
        # Não deve ter chamado commit (item duplicado)
        service.db.commit.assert_not_called()

    async def test_batch_multiplos_itens(self, service, mock_user):
        """Deve processar múltiplos itens independentemente."""
        items = [
            SyncItem(client_id="uuid-1", tipo="invalido", dados={}),
            SyncItem(client_id="uuid-2", tipo="invalido", dados={}),
        ]

        results = await service.process_batch(items, mock_user)

        assert len(results) == 2
        assert all(r.status == "error" for r in results)
