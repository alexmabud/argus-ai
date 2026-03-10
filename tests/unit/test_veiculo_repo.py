"""Testes unitários do VeiculoRepository.

Testa o método get_pessoas_por_veiculo com mock do banco de dados,
verificando os filtros aplicados à query e o retorno correto.
"""

from unittest.mock import AsyncMock, MagicMock

from app.repositories.veiculo_repo import VeiculoRepository


class TestGetPessoasPorVeiculo:
    """Testes do método get_pessoas_por_veiculo."""

    async def test_get_pessoas_por_veiculo_retorna_lista_vazia(self):
        """Retorna lista vazia quando banco não tem resultados.

        Verifica que o método retorna [] quando execute().all() é vazio
        e que db.execute foi chamado exatamente uma vez.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        result = await repo.get_pessoas_por_veiculo(
            placa="XXX", modelo=None, cor=None, guarnicao_id=1
        )

        assert result == []
        db.execute.assert_called_once()

    async def test_get_pessoas_por_veiculo_por_placa(self):
        """Aplica filtro ILIKE normalizado quando placa é informada.

        Verifica que a query SQL compilada contém o padrão ILIKE com a
        placa em uppercase sem traços.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(
            placa="abc-123", modelo=None, cor=None, guarnicao_id=None
        )

        db.execute.assert_called_once()
        call_args = db.execute.call_args
        query = call_args[0][0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "ABC123" in compiled
        assert "LIKE" in compiled.upper()

    async def test_get_pessoas_por_veiculo_por_modelo(self):
        """Aplica filtro ILIKE quando modelo é informado.

        Verifica que a query SQL compilada contém o modelo em cláusula LIKE.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(placa=None, modelo="Gol", cor=None, guarnicao_id=None)

        db.execute.assert_called_once()
        call_args = db.execute.call_args
        query = call_args[0][0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "Gol" in compiled
        assert "LIKE" in compiled.upper()

    async def test_get_pessoas_por_veiculo_com_cor(self):
        """Aplica filtros ILIKE de modelo e cor quando ambos são informados.

        Verifica que a query SQL compilada contém tanto modelo quanto cor
        nas cláusulas de filtro.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(
            placa=None, modelo="Gol", cor="Branco", guarnicao_id=None
        )

        db.execute.assert_called_once()
        call_args = db.execute.call_args
        query = call_args[0][0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "Gol" in compiled
        assert "Branco" in compiled

    async def test_get_pessoas_por_veiculo_retorna_tuplas(self):
        """Retorna lista de tuplas quando banco tem resultados.

        Verifica que o método repassa o resultado de result.all() diretamente
        como lista de tuplas (Pessoa, Veiculo).
        """
        db = AsyncMock()
        mock_result = MagicMock()
        tupla_fake = (MagicMock(), MagicMock())
        mock_result.all.return_value = [tupla_fake]
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        result = await repo.get_pessoas_por_veiculo(
            placa=None, modelo=None, cor=None, guarnicao_id=None
        )

        assert len(result) == 1
        assert result[0] is tupla_fake

    async def test_get_pessoas_por_veiculo_sem_filtros(self):
        """Executa query sem filtros opcionais quando todos são None.

        Verifica que db.execute é chamado uma vez mesmo sem nenhum filtro.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        result = await repo.get_pessoas_por_veiculo(
            placa=None, modelo=None, cor=None, guarnicao_id=None
        )

        assert result == []
        db.execute.assert_called_once()
