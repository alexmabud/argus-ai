"""Testes da cascata de visibilidade de abordagens (permissions).

Cobre ``filtros_abordagem`` (resolução pura equipe > BPM > global) e
``assert_pode_ver_foto_abordagem`` (controle de acesso a mídia de abordagem no
storage), garantindo consistência com consultas/analytics — achado #4 do
Sub-lote 2B.
"""

from types import SimpleNamespace

import pytest

from app.core.exceptions import AcessoNegadoError
from app.core.permissions import assert_pode_ver_foto_abordagem, filtros_abordagem


def _user(*, guarnicao_id, isolamento_equipe=False, bpm_id=None, isolamento_bpm=False):
    """Monta um usuário falso com guarnição/BPM para os testes de cascata.

    Args:
        guarnicao_id: ID da guarnição do usuário.
        isolamento_equipe: Valor de isolamento_abordagens na guarnição.
        bpm_id: ID do BPM da guarnição (opcional).
        isolamento_bpm: Valor de isolamento_abordagens no BPM.

    Returns:
        Objeto SimpleNamespace imitando o usuário com guarnicao e bpm.
    """
    bpm = SimpleNamespace(id=bpm_id, isolamento_abordagens=isolamento_bpm) if bpm_id else None
    guarnicao = SimpleNamespace(
        isolamento_abordagens=isolamento_equipe,
        bpm=bpm,
        bpm_id=bpm_id,
    )
    return SimpleNamespace(guarnicao_id=guarnicao_id, guarnicao=guarnicao)


def test_filtros_abordagem_isolamento_equipe():
    """Isolamento de equipe ativo restringe pela guarnição."""
    user = _user(guarnicao_id=7, isolamento_equipe=True, bpm_id=3, isolamento_bpm=True)
    assert filtros_abordagem(user) == (7, None)


def test_filtros_abordagem_isolamento_bpm():
    """Equipe sem isolamento mas BPM com isolamento restringe pelo BPM."""
    user = _user(guarnicao_id=7, isolamento_equipe=False, bpm_id=3, isolamento_bpm=True)
    assert filtros_abordagem(user) == (None, 3)


def test_filtros_abordagem_global():
    """Sem isolamento em equipe nem BPM, acesso é global."""
    user = _user(guarnicao_id=7, isolamento_equipe=False, bpm_id=3, isolamento_bpm=False)
    assert filtros_abordagem(user) == (None, None)


def test_filtros_abordagem_sem_guarnicao():
    """Usuário sem guarnição cai no global."""
    user = SimpleNamespace(guarnicao_id=None, guarnicao=None)
    assert filtros_abordagem(user) == (None, None)


@pytest.mark.asyncio
async def test_foto_abordagem_global_libera_outra_guarnicao(db_session, bpm, guarnicao):
    """Sem isolamento, foto de outra guarnição é visível (consistente com consultas).

    Args:
        db_session: Sessão do banco de testes.
        bpm: Fixture de BPM.
        guarnicao: Fixture de guarnição (sem isolamento por padrão).
    """
    user = _user(guarnicao_id=guarnicao.id, isolamento_equipe=False, bpm_id=bpm.id)
    foto = SimpleNamespace(guarnicao_id=guarnicao.id + 999, pessoa_id=None)
    # Não deve levantar — modo global.
    await assert_pode_ver_foto_abordagem(db_session, user, foto)


@pytest.mark.asyncio
async def test_foto_abordagem_isolamento_equipe_bloqueia_outra(db_session, guarnicao):
    """Isolamento de equipe bloqueia foto de outra guarnição.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição.
    """
    user = _user(guarnicao_id=guarnicao.id, isolamento_equipe=True)
    foto_propria = SimpleNamespace(guarnicao_id=guarnicao.id, pessoa_id=None)
    foto_alheia = SimpleNamespace(guarnicao_id=guarnicao.id + 999, pessoa_id=None)

    await assert_pode_ver_foto_abordagem(db_session, user, foto_propria)  # ok
    with pytest.raises(AcessoNegadoError):
        await assert_pode_ver_foto_abordagem(db_session, user, foto_alheia)


@pytest.mark.asyncio
async def test_foto_abordagem_isolamento_bpm(db_session, bpm, guarnicao):
    """Isolamento de BPM libera guarnição irmã (mesmo BPM) e bloqueia outro BPM.

    Args:
        db_session: Sessão do banco de testes.
        bpm: Fixture de BPM (mesmo BPM da guarnição da fixture).
        guarnicao: Fixture de guarnição (pertence ao BPM da fixture).
    """
    from app.models.bpm import Bpm
    from app.models.guarnicao import Guarnicao

    # Guarnição irmã no MESMO BPM.
    irma = Guarnicao(nome="Irma", bpm_id=bpm.id, codigo="IRMA-001")
    # BPM diferente + guarnição nele.
    outro_bpm = Bpm(nome="Outro BPM")
    db_session.add_all([irma, outro_bpm])
    await db_session.flush()
    estranha = Guarnicao(nome="Estranha", bpm_id=outro_bpm.id, codigo="ESTR-001")
    db_session.add(estranha)
    await db_session.flush()

    user = _user(
        guarnicao_id=guarnicao.id, isolamento_equipe=False, bpm_id=bpm.id, isolamento_bpm=True
    )

    foto_irma = SimpleNamespace(guarnicao_id=irma.id, pessoa_id=None)
    foto_estranha = SimpleNamespace(guarnicao_id=estranha.id, pessoa_id=None)

    await assert_pode_ver_foto_abordagem(db_session, user, foto_irma)  # mesmo BPM: ok
    with pytest.raises(AcessoNegadoError):
        await assert_pode_ver_foto_abordagem(db_session, user, foto_estranha)
