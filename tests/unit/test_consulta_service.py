"""Testes unitários do ConsultaService.

Testa busca unificada cross-domain, busca por localidades, e busca de
pessoas vinculadas a veículos com deduplicação e paginação.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.usuario import Usuario
from app.services.consulta_service import ConsultaService


class TestPessoasPorVeiculo:
    """Testes para busca de pessoas por veículo."""

    @pytest.mark.asyncio
    async def test_pessoas_por_veiculo_delega_para_repo(self):
        """Testa que pessoas_por_veiculo delega corretamente para veiculo_repo.

        Verifica que:
        1. O método extrai guarnicao_id do user
        2. Passa todos os parâmetros ao repositório
        3. Converte tuplas em dicts com chaves "pessoa" e "veiculo"
        """
        db = AsyncMock()
        service = ConsultaService(db)

        mock_pessoa = MagicMock()
        mock_veiculo = MagicMock()
        service.veiculo_repo.get_pessoas_por_veiculo = AsyncMock(
            return_value=[(mock_pessoa, mock_veiculo)]
        )

        user = MagicMock(spec=Usuario)
        user.guarnicao_id = 42

        result = await service.pessoas_por_veiculo(
            placa="ABC",
            modelo=None,
            cor=None,
            skip=0,
            limit=20,
            user=user,
        )

        assert len(result) == 1
        assert result[0]["pessoa"] is mock_pessoa
        assert result[0]["veiculo"] is mock_veiculo
        service.veiculo_repo.get_pessoas_por_veiculo.assert_called_once_with(
            placa="ABC",
            modelo=None,
            cor=None,
            guarnicao_id=42,
            skip=0,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_pessoas_por_veiculo_com_modelo_e_cor(self):
        """Testa busca com modelo e cor (sem placa).

        Verifica que todos os parâmetros são passados ao repositório.
        """
        db = AsyncMock()
        service = ConsultaService(db)

        mock_pessoa = MagicMock()
        mock_veiculo = MagicMock()
        service.veiculo_repo.get_pessoas_por_veiculo = AsyncMock(
            return_value=[(mock_pessoa, mock_veiculo)]
        )

        user = MagicMock(spec=Usuario)
        user.guarnicao_id = 10

        result = await service.pessoas_por_veiculo(
            placa=None,
            modelo="Civic",
            cor="Branco",
            skip=10,
            limit=50,
            user=user,
        )

        assert len(result) == 1
        service.veiculo_repo.get_pessoas_por_veiculo.assert_called_once_with(
            placa=None,
            modelo="Civic",
            cor="Branco",
            guarnicao_id=10,
            skip=10,
            limit=50,
        )

    @pytest.mark.asyncio
    async def test_pessoas_por_veiculo_retorna_lista_vazia(self):
        """Testa que retorna lista vazia quando repositório não encontra nada."""
        db = AsyncMock()
        service = ConsultaService(db)

        service.veiculo_repo.get_pessoas_por_veiculo = AsyncMock(return_value=[])

        user = MagicMock(spec=Usuario)
        user.guarnicao_id = 42

        result = await service.pessoas_por_veiculo(
            placa="XYZ",
            modelo=None,
            cor=None,
            skip=0,
            limit=20,
            user=user,
        )

        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_pessoas_por_veiculo_multiplos_resultados(self):
        """Testa que converte múltiplas tuplas em dicts corretamente."""
        db = AsyncMock()
        service = ConsultaService(db)

        pessoa1, veiculo1 = MagicMock(), MagicMock()
        pessoa2, veiculo2 = MagicMock(), MagicMock()
        pessoa3, veiculo3 = MagicMock(), MagicMock()

        service.veiculo_repo.get_pessoas_por_veiculo = AsyncMock(
            return_value=[(pessoa1, veiculo1), (pessoa2, veiculo2), (pessoa3, veiculo3)]
        )

        user = MagicMock(spec=Usuario)
        user.guarnicao_id = 42

        result = await service.pessoas_por_veiculo(
            placa="ABC",
            modelo=None,
            cor=None,
            skip=0,
            limit=20,
            user=user,
        )

        assert len(result) == 3
        assert result[0]["pessoa"] is pessoa1
        assert result[0]["veiculo"] is veiculo1
        assert result[1]["pessoa"] is pessoa2
        assert result[1]["veiculo"] is veiculo2
        assert result[2]["pessoa"] is pessoa3
        assert result[2]["veiculo"] is veiculo3

    @pytest.mark.asyncio
    async def test_pessoas_por_veiculo_user_none(self):
        """Testa que extrai guarnicao_id como None quando user é None."""
        db = AsyncMock()
        service = ConsultaService(db)

        mock_pessoa = MagicMock()
        mock_veiculo = MagicMock()
        service.veiculo_repo.get_pessoas_por_veiculo = AsyncMock(
            return_value=[(mock_pessoa, mock_veiculo)]
        )

        result = await service.pessoas_por_veiculo(
            placa="ABC",
            modelo=None,
            cor=None,
            skip=0,
            limit=20,
            user=None,
        )

        assert len(result) == 1
        service.veiculo_repo.get_pessoas_por_veiculo.assert_called_once_with(
            placa="ABC",
            modelo=None,
            cor=None,
            guarnicao_id=None,
            skip=0,
            limit=20,
        )
