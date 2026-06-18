"""Testes de busca textual (search_by_texto) do AbordagemRepository.

Cobre a busca por atributos de veículo (modelo, cor, tipo) no campo `q`
da página de Relatórios, além da placa já suportada.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import AbordagemVeiculo
from app.repositories.abordagem_repo import AbordagemRepository


@pytest.fixture
async def abordagem_com_veiculo(db_session: AsyncSession, abordagem, veiculo):
    """Vincula o veículo de teste (Gol/Branco/Carro/ABC1D23) à abordagem.

    Args:
        db_session: Sessão do banco de testes.
        abordagem: Abordagem da guarnição de teste.
        veiculo: Veículo com modelo 'Gol', cor 'Branco', tipo 'Carro'.

    Returns:
        Abordagem: A abordagem com o veículo vinculado e ativo.
    """
    link = AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id)
    db_session.add(link)
    await db_session.flush()
    return abordagem


@pytest.mark.asyncio
@pytest.mark.parametrize("termo", ["Gol", "Branco", "Carro"])
async def test_search_by_texto_encontra_por_atributo_de_veiculo(
    db_session: AsyncSession, guarnicao, abordagem_com_veiculo, termo
):
    """Busca por modelo, cor ou tipo do veículo retorna a abordagem vinculada.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição da abordagem/veículo.
        abordagem_com_veiculo: Abordagem com veículo vinculado.
        termo: Atributo do veículo usado como termo de busca.
    """
    repo = AbordagemRepository(db_session)
    result = await repo.search_by_texto(q=termo, guarnicao_id=guarnicao.id)
    assert abordagem_com_veiculo.id in [a.id for a in result]


@pytest.mark.asyncio
async def test_search_by_texto_por_placa_ainda_funciona(
    db_session: AsyncSession, guarnicao, abordagem_com_veiculo
):
    """Regressão: busca por placa continua retornando a abordagem.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição da abordagem/veículo.
        abordagem_com_veiculo: Abordagem com veículo vinculado.
    """
    repo = AbordagemRepository(db_session)
    result = await repo.search_by_texto(q="ABC1D23", guarnicao_id=guarnicao.id)
    assert abordagem_com_veiculo.id in [a.id for a in result]
