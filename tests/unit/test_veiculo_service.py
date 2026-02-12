"""Testes unitários do VeiculoService.

Testa criação com normalização de placa, verificação de unicidade,
busca parcial por placa e soft delete.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.schemas.veiculo import VeiculoCreate
from app.services.veiculo_service import VeiculoService


class TestCriarVeiculo:
    """Testes de criação de veículo."""

    async def test_criar_veiculo_normaliza_placa(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que placa é normalizada para uppercase sem traços.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = VeiculoService(db_session)
        data = VeiculoCreate(placa="abc-1d23", modelo="Gol", cor="Branco")
        veiculo = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert veiculo.placa == "ABC1D23"

    async def test_criar_veiculo_placa_duplicada(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa rejeição de placa duplicada no sistema.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = VeiculoService(db_session)
        data1 = VeiculoCreate(placa="ABC1D23", modelo="Gol", cor="Branco")
        await service.criar(data=data1, user_id=usuario.id, guarnicao_id=guarnicao.id)

        data2 = VeiculoCreate(placa="ABC1D23", modelo="Onix", cor="Preto")
        with pytest.raises(ConflitoDadosError):
            await service.criar(data=data2, user_id=usuario.id, guarnicao_id=guarnicao.id)


class TestBuscarVeiculo:
    """Testes de busca de veículo."""

    async def test_buscar_por_id(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa busca de veículo por ID com verificação de tenant.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = VeiculoService(db_session)
        data = VeiculoCreate(placa="XYZ9A99", modelo="Hilux", cor="Prata")
        veiculo = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        encontrado = await service.buscar_por_id(veiculo.id, usuario)
        assert encontrado.placa == "XYZ9A99"

    async def test_buscar_por_id_inexistente(self, db_session: AsyncSession, usuario: Usuario):
        """Testa busca de veículo inexistente retorna NaoEncontradoError.

        Args:
            db_session: Sessão do banco de testes.
            usuario: Fixture de usuário.
        """
        service = VeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.buscar_por_id(99999, usuario)


class TestDesativarVeiculo:
    """Testes de soft delete de veículo."""

    async def test_soft_delete(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa soft delete marca veículo como inativo.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = VeiculoService(db_session)
        data = VeiculoCreate(placa="DEL1E23", modelo="Fiesta", cor="Vermelho")
        veiculo = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        assert veiculo.ativo is True

        desativado = await service.desativar(veiculo.id, usuario)
        assert desativado.ativo is False
