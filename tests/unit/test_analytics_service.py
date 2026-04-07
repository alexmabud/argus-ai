"""Testes unitários para o serviço de analytics.

Valida geração de métricas operacionais: resumo, distribuição
horária, pessoas recorrentes, qualidade RAG e pontos geográficos
de abordagens por dia.
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
        """Deve retornar lista com id, nome, apelido, total, ultima, cpf e foto."""
        from unittest.mock import patch

        db = AsyncMock()
        now = datetime.now(UTC)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (1, "João", "Joãozinho", 5, now, "cpf_enc", "https://r2.example.com/foto.jpg"),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        with patch("app.services.analytics_service.decrypt", return_value="123.456.789-00"):
            result = await service.pessoas_recorrentes(guarnicao_id=1)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["nome"] == "João"
        assert result[0]["total_abordagens"] == 5
        assert result[0]["cpf"] == "123.456.789-00"
        assert result[0]["foto_url"] == "https://r2.example.com/foto.jpg"


class TestMetricasRAG:
    """Testes para AnalyticsService.metricas_rag()."""

    async def test_metricas_rag_retorna_totais(self):
        """Deve retornar total de ocorrências e indexadas."""
        db = AsyncMock()
        mock_total = MagicMock()
        mock_total.scalar.return_value = 10
        mock_indexadas = MagicMock()
        mock_indexadas.scalar.return_value = 7
        db.execute = AsyncMock(side_effect=[mock_total, mock_indexadas])
        service = AnalyticsService(db)

        result = await service.metricas_rag(guarnicao_id=1)

        assert result["total_ocorrencias"] == 10
        assert result["ocorrencias_indexadas"] == 7


class TestResumoHoje:
    """Testes para AnalyticsService.resumo_hoje()."""

    async def test_resumo_hoje_retorna_campos_corretos(self):
        """Deve retornar abordagens e pessoas do dia atual."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [5, 3]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_hoje(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert result["abordagens"] == 5
        assert result["pessoas"] == 3

    async def test_resumo_hoje_sem_dados_retorna_zeros(self):
        """Deve retornar zeros quando não há abordagens hoje."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_hoje(guarnicao_id=1)

        assert result["abordagens"] == 0
        assert result["pessoas"] == 0


class TestResumoMes:
    """Testes para AnalyticsService.resumo_mes()."""

    async def test_resumo_mes_retorna_campos_corretos(self):
        """Deve retornar abordagens e pessoas do mês atual."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [20, 12]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_mes(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert result["abordagens"] == 20
        assert result["pessoas"] == 12


class TestResumoTotal:
    """Testes para AnalyticsService.resumo_total()."""

    async def test_resumo_total_retorna_campos_corretos(self):
        """Deve retornar totais sem filtro de data."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [100, 60, 492]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_total(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert "pessoas_cadastradas" in result
        assert result["abordagens"] == 100
        assert result["pessoas"] == 60
        assert result["pessoas_cadastradas"] == 492


class TestPorDia:
    """Testes para AnalyticsService.por_dia()."""

    async def test_por_dia_retorna_lista_de_dicts(self):
        """Deve retornar lista com data, abordagens e pessoas por dia."""
        from datetime import date as date_type

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (date_type(2026, 3, 14), 3, 5),
            (date_type(2026, 3, 15), 1, 2),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_dia(guarnicao_id=1, dias=30)

        assert len(result) == 2
        assert result[0]["data"] == "2026-03-14"
        assert result[0]["abordagens"] == 3
        assert result[0]["pessoas"] == 5

    async def test_por_dia_sem_dados_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_dia(guarnicao_id=1, dias=30)

        assert result == []


class TestPorMes:
    """Testes para AnalyticsService.por_mes()."""

    async def test_por_mes_retorna_lista_de_dicts(self):
        """Deve retornar lista com mes, abordagens e pessoas por mês."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (2026, 2, 40, 65),
            (2026, 3, 15, 22),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_mes(guarnicao_id=1, meses=12)

        assert len(result) == 2
        assert result[0]["mes"] == "2026-02"
        assert result[0]["abordagens"] == 40
        assert result[0]["pessoas"] == 65

    async def test_por_mes_sem_dados_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_mes(guarnicao_id=1, meses=12)

        assert result == []


class TestDiasComAbordagem:
    """Testes para AnalyticsService.dias_com_abordagem()."""

    async def test_retorna_lista_de_inteiros(self):
        """Deve retornar lista de dias do mês com abordagem."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(14,), (15,), (20,)]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.dias_com_abordagem(guarnicao_id=1, mes="2026-03")

        assert result == [14, 15, 20]

    async def test_sem_abordagens_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens no mês."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.dias_com_abordagem(guarnicao_id=1, mes="2026-03")

        assert result == []


class TestPessoasDoDia:
    """Testes para AnalyticsService.pessoas_do_dia()."""

    async def test_retorna_lista_com_campos_corretos(self):
        """Deve retornar id, nome, cpf e foto_url das pessoas do dia."""
        from unittest.mock import patch

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (1, "João Silva", "cpf_enc", "https://r2.example.com/foto.jpg"),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        with patch("app.services.analytics_service.decrypt", return_value="123.456.789-00"):
            result = await service.pessoas_do_dia(guarnicao_id=1, data="2026-03-14")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["nome"] == "João Silva"
        assert result[0]["cpf"] == "123.456.789-00"
        assert result[0]["foto_url"] == "https://r2.example.com/foto.jpg"

    async def test_sem_pessoas_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens no dia."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.pessoas_do_dia(guarnicao_id=1, data="2026-03-14")

        assert result == []


class TestAbordacoesdoDia:
    """Testes para AnalyticsService.abordagens_do_dia()."""

    @pytest.fixture
    def service(self):
        """Cria instância de AnalyticsService com session mock."""
        db = AsyncMock()
        return AnalyticsService(db)

    async def test_retorna_pontos_com_coordenadas(self, service):
        """Deve retornar lista de pontos com lat, lng e horario."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (-23.5505, -46.6333, datetime(2026, 3, 28, 14, 32, tzinfo=UTC)),
            (-23.5510, -46.6340, datetime(2026, 3, 28, 15, 10, tzinfo=UTC)),
        ]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.abordagens_do_dia(guarnicao_id=1, data="2026-03-28")

        assert len(result) == 2
        assert result[0]["lat"] == -23.5505
        assert result[0]["lng"] == -46.6333
        assert result[0]["horario"] == "14:32"

    async def test_sem_abordagens_retorna_lista_vazia(self, service):
        """Deve retornar lista vazia quando não há abordagens com localização."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.abordagens_do_dia(guarnicao_id=1, data="2026-03-28")

        assert result == []
