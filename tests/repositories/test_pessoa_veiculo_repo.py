"""Testes do PessoaVeiculoRepository — vínculo direto pessoa-veículo.

Verifica busca de par pessoa+veículo (incluindo suporte a soft-deleted
para reativação futura) e listagem de vínculos diretos ativos.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.pessoa_veiculo import PessoaVeiculo
from app.models.veiculo import Veiculo
from app.repositories.pessoa_veiculo_repo import PessoaVeiculoRepository


class TestGetPar:
    """Testes do método get_par."""

    async def test_get_par_ativo(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, guarnicao: Guarnicao
    ):
        """Encontra vínculo ativo entre a pessoa e o veículo informados."""
        vinculo = PessoaVeiculo(
            pessoa_id=pessoa.id, veiculo_id=veiculo.id, guarnicao_id=guarnicao.id
        )
        db_session.add(vinculo)
        await db_session.flush()

        repo = PessoaVeiculoRepository(db_session)
        encontrado = await repo.get_par(pessoa.id, veiculo.id)
        assert encontrado is not None
        assert encontrado.id == vinculo.id

    async def test_get_par_nao_encontra_inativo_por_padrao(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, guarnicao: Guarnicao
    ):
        """Vínculo soft-deleted não aparece por padrão, mas aparece com include_inactive."""
        vinculo = PessoaVeiculo(
            pessoa_id=pessoa.id, veiculo_id=veiculo.id, guarnicao_id=guarnicao.id, ativo=False
        )
        db_session.add(vinculo)
        await db_session.flush()

        repo = PessoaVeiculoRepository(db_session)
        assert await repo.get_par(pessoa.id, veiculo.id) is None
        assert await repo.get_par(pessoa.id, veiculo.id, include_inactive=True) is not None


class TestListarDiretos:
    """Testes do método listar_diretos."""

    async def test_lista_so_ativos(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, guarnicao: Guarnicao
    ):
        """Retorna apenas vínculos ativos, ignorando os soft-deleted."""
        v2 = Veiculo(placa="ZZZ9Z99", guarnicao_id=guarnicao.id)
        db_session.add(v2)
        await db_session.flush()

        ativo = PessoaVeiculo(pessoa_id=pessoa.id, veiculo_id=veiculo.id, guarnicao_id=guarnicao.id)
        inativo = PessoaVeiculo(
            pessoa_id=pessoa.id, veiculo_id=v2.id, guarnicao_id=guarnicao.id, ativo=False
        )
        db_session.add_all([ativo, inativo])
        await db_session.flush()

        repo = PessoaVeiculoRepository(db_session)
        diretos = await repo.listar_diretos(pessoa.id)
        assert len(diretos) == 1
        assert diretos[0].veiculo_id == veiculo.id

    async def test_nao_lista_vinculo_com_veiculo_desativado(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, guarnicao: Guarnicao
    ):
        """Vínculo ativo cujo Veiculo está soft-deletado não é retornado.

        Paridade defensiva com get_veiculos_por_pessoa_via_abordagem, que já
        exclui veículos inativos — hoje não há rota de desativar veículo,
        mas o service (VeiculoService.desativar) já existe.
        """
        vinculo = PessoaVeiculo(
            pessoa_id=pessoa.id, veiculo_id=veiculo.id, guarnicao_id=guarnicao.id
        )
        db_session.add(vinculo)
        await db_session.flush()

        veiculo.ativo = False
        await db_session.flush()

        repo = PessoaVeiculoRepository(db_session)
        diretos = await repo.listar_diretos(pessoa.id)
        assert diretos == []
