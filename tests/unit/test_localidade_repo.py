"""Testes unitários do LocalidadeRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.localidade import Localidade
from app.repositories.localidade_repo import LocalidadeRepository


@pytest.mark.asyncio
async def test_listar_estados(db_session: AsyncSession):
    """Deve retornar todos os estados ativos ordenados por nome_exibicao."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    assert len(estados) == 27
    assert all(e.tipo == "estado" for e in estados)


@pytest.mark.asyncio
async def test_autocomplete_cidade(db_session: AsyncSession):
    """Deve retornar cidades do estado filtradas pelo texto."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    sp = next((e for e in estados if e.sigla == "SP"), None)
    assert sp is not None, "Estado SP não encontrado — verifique o seed no conftest"

    cidade = Localidade(
        nome="sao paulo",
        nome_exibicao="São Paulo",
        tipo="cidade",
        parent_id=sp.id,
    )
    db_session.add(cidade)
    await db_session.flush()

    resultados = await repo.autocomplete(tipo="cidade", parent_id=sp.id, q="sao")
    assert any(r.id == cidade.id for r in resultados)


@pytest.mark.asyncio
async def test_autocomplete_retorna_max_10(db_session: AsyncSession):
    """Deve retornar no máximo 10 resultados."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    sp = next((e for e in estados if e.sigla == "SP"), None)
    assert sp is not None, "Estado SP não encontrado — verifique o seed no conftest"

    for i in range(15):
        db_session.add(
            Localidade(
                nome=f"cidade {i:02d}",
                nome_exibicao=f"Cidade {i:02d}",
                tipo="cidade",
                parent_id=sp.id,
            )
        )
    await db_session.flush()

    resultados = await repo.autocomplete(tipo="cidade", parent_id=sp.id, q="cidade", limit=10)
    assert len(resultados) <= 10


@pytest.mark.asyncio
async def test_buscar_por_nome_e_parent(db_session: AsyncSession):
    """Deve encontrar localidade exata pelo nome normalizado e parent_id."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    rj = next((e for e in estados if e.sigla == "RJ"), None)
    assert rj is not None, "Estado RJ não encontrado — verifique o seed no conftest"

    cidade = Localidade(
        nome="rio de janeiro",
        nome_exibicao="Rio de Janeiro",
        tipo="cidade",
        parent_id=rj.id,
    )
    db_session.add(cidade)
    await db_session.flush()

    encontrada = await repo.buscar_por_nome_e_parent("rio de janeiro", "cidade", rj.id)
    assert encontrada is not None
    assert encontrada.id == cidade.id


@pytest.mark.asyncio
async def test_autocomplete_sem_q_retorna_todos(db_session: AsyncSession):
    """Sem q, retorna todos os filhos do parent_id sem filtro de texto."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    mg = next((e for e in estados if e.sigla == "MG"), None)
    assert mg is not None, "Estado MG não encontrado — verifique o seed no conftest"

    for nome in ["alfa", "beta", "gamma"]:
        db_session.add(
            Localidade(
                nome=nome,
                nome_exibicao=nome.capitalize(),
                tipo="cidade",
                parent_id=mg.id,
            )
        )
    await db_session.flush()

    result = await repo.autocomplete(tipo="cidade", parent_id=mg.id, q=None)
    assert len(result) >= 3
