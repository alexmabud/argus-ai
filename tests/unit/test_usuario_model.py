"""Testes do model Usuario — validação dos novos campos de perfil e sessão."""

from app.models.usuario import POSTOS_GRADUACAO, Usuario


def test_postos_graduacao_lista_completa():
    """Verifica que a lista de postos contém as graduações PM esperadas."""
    assert "Soldado" in POSTOS_GRADUACAO
    assert "Coronel" in POSTOS_GRADUACAO
    assert len(POSTOS_GRADUACAO) == 13


def test_usuario_possui_campos_de_perfil():
    """Verifica que o model Usuario possui os novos atributos de perfil."""
    u = Usuario(nome="Teste", matricula="T001", senha_hash="hash")
    assert hasattr(u, "posto_graduacao")
    assert hasattr(u, "nome_guerra")
    assert hasattr(u, "foto_url")
    assert hasattr(u, "session_id")
    assert u.posto_graduacao is None
    assert u.nome_guerra is None
    assert u.foto_url is None
    assert u.session_id is None
