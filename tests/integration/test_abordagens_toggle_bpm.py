"""Testes do toggle de isolamento de abordagens por BPM."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_senha
from app.models.abordagem import Abordagem
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


@pytest.fixture
async def bpm_b(db_session: AsyncSession) -> Bpm:
    """Segundo BPM para testes de isolamento.

    Args:
        db_session: Sessão do banco de testes.

    Returns:
        Bpm: Segundo BPM criado para testes.
    """
    b = Bpm(nome="BPM B")
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.fixture
async def equipe_bpm_b(db_session: AsyncSession, bpm_b: Bpm) -> Guarnicao:
    """Equipe pertencente ao BPM B.

    Args:
        db_session: Sessão do banco de testes.
        bpm_b: BPM B ao qual a equipe pertence.

    Returns:
        Guarnicao: Equipe do BPM B.
    """
    g = Guarnicao(nome="GU BPM-B", bpm_id=bpm_b.id, codigo="BPMB-GU01")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_bpm_b(db_session: AsyncSession, equipe_bpm_b: Guarnicao) -> Usuario:
    """Usuário pertencente ao BPM B.

    Args:
        db_session: Sessão do banco de testes.
        equipe_bpm_b: Equipe do BPM B à qual o usuário pertence.

    Returns:
        Usuario: Usuário membro do BPM B.
    """
    u = Usuario(
        nome="Agente BPM-B",
        matricula="BPMB001",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=equipe_bpm_b.id,
        session_id="session-bpmb",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def abordagem_bpm_b(
    db_session: AsyncSession, equipe_bpm_b: Guarnicao, usuario_bpm_b: Usuario
) -> Abordagem:
    """Abordagem registrada pelo BPM B.

    Args:
        db_session: Sessão do banco de testes.
        equipe_bpm_b: Equipe do BPM B que registrou a abordagem.
        usuario_bpm_b: Usuário do BPM B que registrou a abordagem.

    Returns:
        Abordagem: Abordagem pertencente ao BPM B.
    """
    a = Abordagem(
        guarnicao_id=equipe_bpm_b.id,
        usuario_id=usuario_bpm_b.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av BPM-B 300",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_isolamento_bpm_off_usuario_a_ve_abordagem_de_bpm_b(
    client: AsyncClient, auth_headers, abordagem, abordagem_bpm_b, bpm
):
    """Com isolamento BPM OFF, usuário do BPM A vê abordagens do BPM B.

    Args:
        client: Cliente HTTP assincrónico.
        auth_headers: Headers do usuário do BPM A.
        abordagem: Abordagem do BPM A.
        abordagem_bpm_b: Abordagem do BPM B.
        bpm: BPM A (deve estar com isolamento desligado).
    """
    assert bpm.isolamento_abordagens is False
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_bpm_b.id in ids


@pytest.mark.asyncio
async def test_isolamento_bpm_on_usuario_a_nao_ve_abordagem_de_bpm_b(
    client: AsyncClient, auth_headers, db_session, bpm, abordagem, abordagem_bpm_b
):
    """Com isolamento BPM ON, usuário do BPM A não vê abordagens do BPM B.

    Args:
        client: Cliente HTTP assincrónico.
        auth_headers: Headers do usuário do BPM A.
        db_session: Sessão do banco de testes para alterar o isolamento.
        bpm: BPM A a ter isolamento ativado.
        abordagem: Abordagem do BPM A (deve aparecer).
        abordagem_bpm_b: Abordagem do BPM B (não deve aparecer).
    """
    bpm.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_bpm_b.id not in ids


@pytest.mark.asyncio
async def test_isolamento_equipe_prevalece_sobre_bpm(
    client: AsyncClient, auth_headers, db_session, bpm, guarnicao, abordagem, abordagem_bpm_b
):
    """Quando isolamento de equipe está ON, usuário vê apenas sua equipe.

    Mesmo com BPM isolamento ativo, o filtro de equipe prevalece e o
    usuário não vê abordagens de outras equipes do mesmo BPM.

    Args:
        client: Cliente HTTP assincrónico.
        auth_headers: Headers do usuário do BPM A.
        db_session: Sessão do banco de testes.
        bpm: BPM A a ter isolamento ativado.
        guarnicao: Equipe do usuário com isolamento ativado.
        abordagem: Abordagem da equipe do usuário (deve aparecer).
        abordagem_bpm_b: Abordagem do BPM B (não deve aparecer).
    """
    bpm.isolamento_abordagens = True
    guarnicao.isolamento_abordagens = True
    await db_session.flush()

    equipe_2 = Guarnicao(nome="GU 2 BPM A", bpm_id=bpm.id, codigo="BPMA-GU02")
    db_session.add(equipe_2)
    await db_session.flush()
    usuario_2 = Usuario(
        nome="Agente 2 BPM A",
        matricula="BPMA002",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=equipe_2.id,
        session_id="sess-a2",
    )
    db_session.add(usuario_2)
    await db_session.flush()
    abordagem_equipe_2 = Abordagem(
        guarnicao_id=equipe_2.id,
        usuario_id=usuario_2.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av GU2 BPM-A",
    )
    db_session.add(abordagem_equipe_2)
    await db_session.flush()

    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_equipe_2.id not in ids
    assert abordagem_bpm_b.id not in ids
