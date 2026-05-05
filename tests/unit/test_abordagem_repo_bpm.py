"""Testes dos métodos *_by_bpm() do AbordagemRepository."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.repositories.abordagem_repo import AbordagemRepository


@pytest.fixture
async def bpm2(db_session: AsyncSession, bpm):
    """Segundo BPM para testes de isolamento.

    Args:
        db_session: Sessão do banco de testes.
        bpm: BPM principal da fixture global.

    Returns:
        Bpm: Segundo BPM criado para testar isolamento.
    """
    from app.models.bpm import Bpm

    b = Bpm(nome="Outro BPM")
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.fixture
async def guarnicao_bpm2(db_session: AsyncSession, bpm2):
    """Equipe pertencente ao BPM 2.

    Args:
        db_session: Sessão do banco de testes.
        bpm2: BPM do qual esta equipe faz parte.

    Returns:
        Guarnicao: Equipe do segundo BPM.
    """
    from app.models.guarnicao import Guarnicao

    g = Guarnicao(nome="GU BPM2", bpm_id=bpm2.id, codigo="BPM2-GU01")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_bpm2(db_session: AsyncSession, guarnicao_bpm2):
    """Usuário pertencente ao BPM 2.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao_bpm2: Equipe do BPM 2 à qual o usuário pertence.

    Returns:
        Usuario: Usuário membro da equipe do BPM 2.
    """
    from app.core.security import hash_senha
    from app.models.usuario import Usuario

    u = Usuario(
        nome="Agente BPM2",
        matricula="BPM2001",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=guarnicao_bpm2.id,
        session_id="session-bpm2",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def abordagem_bpm2(db_session: AsyncSession, guarnicao_bpm2, usuario_bpm2):
    """Abordagem registrada por equipe do BPM 2.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao_bpm2: Equipe do BPM 2 que registrou a abordagem.
        usuario_bpm2: Usuário do BPM 2 que registrou a abordagem.

    Returns:
        Abordagem: Abordagem pertencente ao BPM 2.
    """
    a = Abordagem(
        guarnicao_id=guarnicao_bpm2.id,
        usuario_id=usuario_bpm2.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av BPM2 200",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_list_by_bpm_retorna_apenas_do_bpm(
    db_session: AsyncSession, bpm, abordagem, abordagem_bpm2
):
    """list_by_bpm retorna abordagens apenas do BPM especificado."""
    repo = AbordagemRepository(db_session)
    result = await repo.list_by_bpm(bpm_id=bpm.id)
    ids = [a.id for a in result]
    assert abordagem.id in ids
    assert abordagem_bpm2.id not in ids


@pytest.mark.asyncio
async def test_list_by_bpm_nao_retorna_de_outro_bpm(
    db_session: AsyncSession, bpm2, abordagem, abordagem_bpm2
):
    """list_by_bpm com bpm2 não retorna abordagem do bpm1."""
    repo = AbordagemRepository(db_session)
    result = await repo.list_by_bpm(bpm_id=bpm2.id)
    ids = [a.id for a in result]
    assert abordagem_bpm2.id in ids
    assert abordagem.id not in ids


@pytest.mark.asyncio
async def test_get_detail_by_bpm_retorna_abordagem_correta(
    db_session: AsyncSession, bpm, abordagem
):
    """get_detail_by_bpm retorna abordagem se pertence ao BPM."""
    repo = AbordagemRepository(db_session)
    result = await repo.get_detail_by_bpm(abordagem.id, bpm.id)
    assert result is not None
    assert result.id == abordagem.id


@pytest.mark.asyncio
async def test_get_detail_by_bpm_retorna_none_para_outro_bpm(
    db_session: AsyncSession, bpm2, abordagem
):
    """get_detail_by_bpm retorna None se abordagem pertence a BPM diferente."""
    repo = AbordagemRepository(db_session)
    result = await repo.get_detail_by_bpm(abordagem.id, bpm2.id)
    assert result is None
