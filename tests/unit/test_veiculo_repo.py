"""Testes unitários do VeiculoRepository.

Testa o método get_pessoas_por_veiculo com mock do banco de dados,
verificando os filtros aplicados à query e o retorno correto. Também
testa get_veiculos_por_pessoa_via_abordagem com banco de dados real,
verificando a resolução de Pessoa → AbordagemPessoa → AbordagemVeiculo.
"""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem, AbordagemPessoa, AbordagemVeiculo
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.veiculo import Veiculo
from app.repositories.veiculo_repo import VeiculoRepository


class TestGetPessoasPorVeiculo:
    """Testes do método get_pessoas_por_veiculo."""

    async def test_get_pessoas_por_veiculo_retorna_lista_vazia(self):
        """Retorna lista vazia quando banco não tem resultados.

        Verifica que o método retorna [] quando execute().all() é vazio.
        Nota: quando placa é fornecida, debug logging executa queries extras
        intermediárias [DEBUG-pv01]; por isso verificamos apenas que o
        método foi chamado e não o count exato de execuções.
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
        assert db.execute.called

    async def test_get_pessoas_por_veiculo_por_placa(self):
        """Aplica filtro ILIKE normalizado quando placa é informada.

        Verifica que a query SQL compilada contém o padrão ILIKE com a
        placa em uppercase sem traços. O último call é sempre a query
        principal (debug queries intermediárias [DEBUG-pv01] vêm antes).
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(
            placa="abc-123", modelo=None, cor=None, guarnicao_id=None
        )

        assert db.execute.called
        # A query principal é sempre o último call (debug calls vêm antes)
        call_args = db.execute.call_args
        query = call_args[0][0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "ABC123" in compiled
        assert "LIKE" in compiled.upper()

    async def test_get_pessoas_por_veiculo_por_modelo(self):
        """Aplica filtros ILIKE de word-boundary quando modelo é informado.

        Verifica que a query SQL compilada usa OR com múltiplos padrões ILIKE
        (exato, prefixo, sufixo, meio) em vez de substring %modelo%.
        Isso garante que "Gol" não corresponda a "Golf".
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
        # Verifica padrão word-boundary: não deve usar substring genérica %Gol%
        assert "%Gol%" not in compiled
        # Deve ter múltiplos padrões OR para cobrir posição do modelo
        assert "Gol %" in compiled or "% Gol" in compiled

    async def test_get_pessoas_por_veiculo_modelo_trim(self):
        """Remove espaços do modelo antes de aplicar o filtro.

        Verifica que "Golf " (com espaço trailing) gera o mesmo SQL que "Golf",
        corrigindo o bug em que espaço trailing eliminava todos os resultados.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(placa=None, modelo="Golf ", cor=None, guarnicao_id=None)

        db.execute.assert_called_once()
        call_args = db.execute.call_args
        query = call_args[0][0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        # Com trim, o padrão de prefixo é 'Golf %' (um espaço).
        # Sem trim, seria 'Golf  %' (dois espaços). Verifica que trim foi aplicado.
        assert "Golf  " not in compiled
        assert "Golf" in compiled

    async def test_modelo_gol_nao_corresponde_golf(self):
        """Padrões word-boundary para "Gol" não cobrem a string "Golf".

        Garante o invariante central do fix: buscar "Gol" não deve retornar
        veículos com modelo "Golf". Verifica diretamente os padrões SQL gerados.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        await repo.get_pessoas_por_veiculo(placa=None, modelo="Gol", cor=None, guarnicao_id=None)

        db.execute.assert_called_once()
        compiled = str(db.execute.call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
        # Extrai todos os padrões ILIKE gerados
        import re as _re

        patterns = _re.findall(r"ILIKE '([^']*)'", compiled, _re.IGNORECASE)
        # Nenhum padrão deve cobrir a string "Golf" (a não ser que Golf seja o exato termo buscado)
        for pat in patterns:
            # Converte padrão ILIKE em regex: % → .*, _ → .
            regex = pat.replace("%", ".*").replace("_", ".")
            assert not _re.fullmatch(regex, "Golf", _re.IGNORECASE), (
                f"Padrão ILIKE '{pat}' cobre indevidamente 'Golf'"
            )

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
        como lista de tuplas (Pessoa, Veiculo) quando há um filtro válido.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        tupla_fake = (MagicMock(), MagicMock())
        mock_result.all.return_value = [tupla_fake]
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        result = await repo.get_pessoas_por_veiculo(
            placa="ABC1D23", modelo=None, cor=None, guarnicao_id=None
        )

        assert len(result) == 1
        assert result[0] is tupla_fake

    async def test_get_pessoas_por_veiculo_sem_filtros_nao_casa_tudo(self):
        """Sem nenhum filtro efetivo, retorna [] SEM executar query (#2 auditoria).

        Guarda defensiva: ausência de filtro não pode virar busca global
        (match-all). O método deve curto-circuitar antes de tocar o banco.
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
        db.execute.assert_not_called()

    async def test_get_pessoas_por_veiculo_placa_normaliza_vazio_nao_casa_tudo(self):
        """Placa que normaliza para vazio (ex.: '--') não pode virar match-all (#2).

        '--' perde os traços na normalização e viraria ILIKE '%%'. A guarda
        deve curto-circuitar e retornar [] sem executar query.
        """
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        repo = VeiculoRepository(db)
        result = await repo.get_pessoas_por_veiculo(
            placa="--", modelo=None, cor=None, guarnicao_id=None
        )

        assert result == []
        db.execute.assert_not_called()


class TestGetVeiculosPorPessoaViaAbordagem:
    """Testes do método get_veiculos_por_pessoa_via_abordagem (banco real).

    Diferente das demais classes deste módulo, usa db_session real (não
    mock) pois valida joins entre três tabelas (Pessoa, AbordagemPessoa,
    AbordagemVeiculo, Veiculo) — mockar a query não verificaria o
    comportamento do join nem o filtro OR sobre pessoa_id.
    """

    async def test_inclui_veiculo_com_pessoa_id_igual(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        abordagem: Abordagem,
    ):
        """Veículo explicitamente atribuído à pessoa na abordagem é retornado."""
        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        db_session.add(
            AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=pessoa.id)
        )
        await db_session.flush()

        repo = VeiculoRepository(db_session)
        resultado = await repo.get_veiculos_por_pessoa_via_abordagem(pessoa.id)
        assert [v.id for v in resultado] == [veiculo.id]

    async def test_inclui_veiculo_com_pessoa_id_nulo(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        abordagem: Abordagem,
    ):
        """Veículo órfão (sem pessoa atribuída) na mesma abordagem também é retornado."""
        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        db_session.add(
            AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=None)
        )
        await db_session.flush()

        repo = VeiculoRepository(db_session)
        resultado = await repo.get_veiculos_por_pessoa_via_abordagem(pessoa.id)
        assert [v.id for v in resultado] == [veiculo.id]

    async def test_nao_inclui_veiculo_de_outra_pessoa_na_mesma_abordagem(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        abordagem: Abordagem,
        guarnicao: Guarnicao,
    ):
        """Veículo atribuído a outra pessoa na mesma abordagem não é retornado."""
        outra = Pessoa(nome="Outra", guarnicao_id=guarnicao.id)
        db_session.add(outra)
        await db_session.flush()

        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        db_session.add(
            AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=outra.id)
        )
        await db_session.flush()

        repo = VeiculoRepository(db_session)
        resultado = await repo.get_veiculos_por_pessoa_via_abordagem(pessoa.id)
        assert resultado == []
