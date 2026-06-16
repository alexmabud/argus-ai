"""Testes do model Usuario — validação dos novos campos de perfil e sessão."""

import pytest

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


@pytest.mark.asyncio
async def test_usuario_flags_admin_default_false(db_session, guarnicao):
    """Novo usuário nasce sem nenhuma flag de admin (menor privilégio)."""
    from app.core.security import hash_senha

    u = Usuario(
        nome="Fulano",
        matricula="FLAGS001",
        senha_hash=hash_senha("x"),
        guarnicao_id=guarnicao.id,
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.refresh(u)

    assert u.is_super_admin is False
    assert u.pode_criar_usuario is False
    assert u.pode_gerar_senha is False
    assert u.pode_pausar is False
    assert u.pode_mover_equipe is False
    assert u.pode_gerir_equipes is False
    assert u.admin_global is False
