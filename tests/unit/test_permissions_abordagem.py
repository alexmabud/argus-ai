"""Testes da cascata de visibilidade de abordagens (permissions.filtros_abordagem).

Cobre a resolução pura equipe > BPM > global usada na LISTAGEM de
relatórios/consultas. (Mídia de abordagem no /storage é global — não usa esta
cascata; ver app/main.py.)
"""

from types import SimpleNamespace

from app.core.permissions import filtros_abordagem


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
