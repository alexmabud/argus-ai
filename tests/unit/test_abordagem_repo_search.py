"""Testes de busca textual (search_by_texto) do AbordagemRepository.

Cobre a busca por atributos de veículo (modelo, cor, tipo) no campo `q`
da página de Relatórios, além da placa já suportada.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem, AbordagemVeiculo
from app.models.veiculo import Veiculo
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


@pytest.fixture
async def abordagem_com_golf(db_session: AsyncSession, guarnicao, usuario):
    """Segunda abordagem com veículo modelo 'Golf' (para testar gol ≠ golf).

    Endereço/cor/tipo/placa deliberadamente sem o termo 'gol' para que o
    único vetor de match de 'Gol' seja o modelo.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição da abordagem/veículo.
        usuario: Usuário que registrou a abordagem.

    Returns:
        Abordagem: Abordagem com veículo modelo 'Golf' vinculado.
    """
    ab = Abordagem(
        data_hora=datetime.now(UTC),
        endereco_texto="Rua das Flores, 50",
        usuario_id=usuario.id,
        guarnicao_id=guarnicao.id,
    )
    db_session.add(ab)
    await db_session.flush()
    v = Veiculo(
        placa="GLF2E34", modelo="Golf", cor="Preto", tipo="Carro", guarnicao_id=guarnicao.id
    )
    db_session.add(v)
    await db_session.flush()
    db_session.add(AbordagemVeiculo(abordagem_id=ab.id, veiculo_id=v.id))
    await db_session.flush()
    return ab


@pytest.mark.asyncio
async def test_search_modelo_gol_nao_corresponde_golf(
    db_session: AsyncSession, guarnicao, abordagem_com_veiculo, abordagem_com_golf
):
    """Busca 'Gol' retorna a abordagem do Gol, mas não a do Golf (word-boundary).

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição das abordagens.
        abordagem_com_veiculo: Abordagem com veículo modelo 'Gol'.
        abordagem_com_golf: Abordagem com veículo modelo 'Golf'.
    """
    repo = AbordagemRepository(db_session)
    result = await repo.search_by_texto(q="Gol", guarnicao_id=guarnicao.id)
    ids = [a.id for a in result]
    assert abordagem_com_veiculo.id in ids
    assert abordagem_com_golf.id not in ids


@pytest.mark.asyncio
async def test_search_cor_feminina_encontra_masculina(
    db_session: AsyncSession, guarnicao, abordagem_com_veiculo
):
    """Busca por 'branca' (feminino) encontra o veículo cadastrado como 'Branco'.

    Regressão da flexão de gênero aplicada no nível do repositório.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição da abordagem/veículo.
        abordagem_com_veiculo: Abordagem com veículo cor 'Branco'.
    """
    repo = AbordagemRepository(db_session)
    result = await repo.search_by_texto(q="branca", guarnicao_id=guarnicao.id)
    assert abordagem_com_veiculo.id in [a.id for a in result]


@pytest.mark.asyncio
async def test_search_modelo_e_cor_tokenizado(
    db_session: AsyncSession, guarnicao, abordagem_com_veiculo, abordagem_com_golf
):
    """Busca 'gol branca' casa cada palavra em algum campo (modelo E cor).

    O Gol branco casa: 'gol' no modelo (word-boundary) E 'branca' na cor (flexão
    encontra 'Branco'). O Golf preto NÃO casa: 'gol' não é palavra em 'Golf' e
    'branca' não casa 'Preto'.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição das abordagens.
        abordagem_com_veiculo: Abordagem do Gol branco.
        abordagem_com_golf: Abordagem do Golf preto.
    """
    repo = AbordagemRepository(db_session)
    result = await repo.search_by_texto(q="gol branca", guarnicao_id=guarnicao.id)
    ids = [a.id for a in result]
    assert abordagem_com_veiculo.id in ids
    assert abordagem_com_golf.id not in ids
