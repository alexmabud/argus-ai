"""Testes do filtro de pessoas por id de localidade (cascade da Consulta)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endereco import EnderecoPessoa
from app.models.localidade import Localidade
from app.repositories.pessoa_repo import PessoaRepository


@pytest.fixture
async def pessoa_com_localidade(db_session: AsyncSession, pessoa):
    """Cria estado/cidade/bairro e um EnderecoPessoa da pessoa vinculado por id.

    Args:
        db_session: Sessão do banco de testes.
        pessoa: Pessoa de teste (fixture global).

    Returns:
        dict: {pessoa, estado_id, cidade_id, bairro_id, outro_estado_id}.
    """
    estado = Localidade(
        nome="distrito federal", nome_exibicao="Distrito Federal", tipo="estado", sigla="DF"
    )
    outro = Localidade(nome="goias", nome_exibicao="Goiás", tipo="estado", sigla="GO")
    db_session.add_all([estado, outro])
    await db_session.flush()
    cidade = Localidade(
        nome="brasilia", nome_exibicao="Brasília", tipo="cidade", parent_id=estado.id
    )
    db_session.add(cidade)
    await db_session.flush()
    bairro = Localidade(
        nome="asa norte", nome_exibicao="Asa Norte", tipo="bairro", parent_id=cidade.id
    )
    db_session.add(bairro)
    await db_session.flush()
    end = EnderecoPessoa(
        pessoa_id=pessoa.id,
        endereco="SQN 100",
        estado_id=estado.id,
        cidade_id=cidade.id,
        bairro_id=bairro.id,
    )
    db_session.add(end)
    await db_session.flush()
    return {
        "pessoa": pessoa,
        "estado_id": estado.id,
        "cidade_id": cidade.id,
        "bairro_id": bairro.id,
        "outro_estado_id": outro.id,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("nivel", ["estado", "cidade", "bairro"])
async def test_filtra_por_id_de_localidade(db_session, pessoa_com_localidade, nivel):
    """Filtrar por estado_id, +cidade_id e +bairro_id retorna a pessoa.

    Args:
        db_session: Sessão do banco de testes.
        pessoa_com_localidade: Pessoa com endereço vinculado por id.
        nivel: Nível de profundidade do filtro aplicado.
    """
    d = pessoa_com_localidade
    repo = PessoaRepository(db_session)
    kwargs = {
        "estado_id": d["estado_id"],
        "cidade_id": None,
        "bairro_id": None,
        "guarnicao_id": None,
    }
    if nivel in ("cidade", "bairro"):
        kwargs["cidade_id"] = d["cidade_id"]
    if nivel == "bairro":
        kwargs["bairro_id"] = d["bairro_id"]
    result = await repo.search_by_localidade_ids_com_endereco(**kwargs)
    assert d["pessoa"].id in [p.id for p, _ in result]


@pytest.mark.asyncio
async def test_estado_diferente_nao_retorna(db_session, pessoa_com_localidade):
    """Filtrar por outro estado_id não retorna a pessoa.

    Args:
        db_session: Sessão do banco de testes.
        pessoa_com_localidade: Pessoa com endereço vinculado por id.
    """
    d = pessoa_com_localidade
    repo = PessoaRepository(db_session)
    result = await repo.search_by_localidade_ids_com_endereco(
        estado_id=d["outro_estado_id"], cidade_id=None, bairro_id=None, guarnicao_id=None
    )
    assert d["pessoa"].id not in [p.id for p, _ in result]
