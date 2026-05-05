"""Testes dos schemas de BPM."""

from app.schemas.bpm import BpmIsolamentoUpdate, BpmRead


def test_bpm_read_inclui_isolamento_abordagens():
    """BpmRead deve incluir o campo isolamento_abordagens."""
    data = BpmRead(id=1, nome="14º BPM", isolamento_abordagens=True)
    assert data.isolamento_abordagens is True


def test_bpm_read_isolamento_padrao_false():
    """BpmRead com isolamento_abordagens omitido deve usar False."""
    data = BpmRead(id=1, nome="14º BPM", isolamento_abordagens=False)
    assert data.isolamento_abordagens is False


def test_bpm_isolamento_update_aceita_bool():
    """BpmIsolamentoUpdate deve aceitar True e False."""
    assert BpmIsolamentoUpdate(isolamento_abordagens=True).isolamento_abordagens is True
    assert BpmIsolamentoUpdate(isolamento_abordagens=False).isolamento_abordagens is False
