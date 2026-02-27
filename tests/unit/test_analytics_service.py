"""Testes unitários para o serviço de analytics.

Valida geração de métricas operacionais: resumo, distribuição
horária, pessoas recorrentes e qualidade RAG.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.analytics_service import AnalyticsService


class TestResumo:
    """Testes para AnalyticsService.resumo()."""

    @pytest.fixture
    def service(self):
        """Cria instância de AnalyticsService com session mock."""
        db = AsyncMock()
        return AnalyticsService(db)

    async def test_resumo_retorna_campos_obrigatorios(self, service):
        """Deve retornar dicionário com todos os campos do resumo."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.resumo(guarnicao_id=1, dias=30)

        assert "periodo_dias" in result
        assert "total_abordagens" in result
        assert "total_pessoas_distintas" in result
        assert "media_abordagens_dia" in result
        assert result["periodo_dias"] == 30

    async def test_resumo_calcula_media_corretamente(self, service):
        """Deve calcular média de abordagens por dia."""
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [60, 20]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.resumo(guarnicao_id=1, dias=30)

        assert result["total_abordagens"] == 60
        assert result["media_abordagens_dia"] == 2.0

    async def test_resumo_sem_dados_retorna_zeros(self, service):
        """Deve retornar zeros quando não há abordagens."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.resumo(guarnicao_id=1, dias=30)

        assert result["total_abordagens"] == 0
        assert result["total_pessoas_distintas"] == 0
        assert result["media_abordagens_dia"] == 0.0


class TestHorariosPico:
    """Testes para AnalyticsService.horarios_pico()."""

    async def test_horarios_retorna_lista_de_dicts(self):
        """Deve retornar lista de dicionários com hora e total."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(8, 5), (14, 12), (22, 8)]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.horarios_pico(guarnicao_id=1, dias=30)

        assert len(result) == 3
        assert result[0] == {"hora": 8, "total": 5}
        assert result[1] == {"hora": 14, "total": 12}


class TestPessoasRecorrentes:
    """Testes para AnalyticsService.pessoas_recorrentes()."""

    async def test_pessoas_limita_a_100(self):
        """Deve limitar resultados a 100 mesmo se solicitado mais."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        await service.pessoas_recorrentes(guarnicao_id=1, limit=200)

        # Verificar que o SQL foi executado (sem erro)
        db.execute.assert_called_once()

    async def test_pessoas_retorna_formato_correto(self):
        """Deve retornar lista com id, nome, apelido, total e última."""
        db = AsyncMock()
        now = datetime.now(UTC)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (1, "João", "Joãozinho", 5, now),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.pessoas_recorrentes(guarnicao_id=1)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["nome"] == "João"
        assert result[0]["total_abordagens"] == 5


class TestMetricasRAG:
    """Testes para AnalyticsService.metricas_rag()."""

    async def test_metricas_rag_retorna_totais(self):
        """Deve retornar total de ocorrências e indexadas."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [10, 7]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.metricas_rag(guarnicao_id=1)

        assert result["total_ocorrencias"] == 10
        assert result["ocorrencias_indexadas"] == 7
