"""Testes dos schemas de admin granular."""

from app.schemas.auth import AdminPermissoesUpdate, AdminRead


def test_admin_permissoes_update_defaults_false():
    """Sem campos, tudo é False (menor privilégio) e is_admin False."""
    p = AdminPermissoesUpdate()
    assert p.is_admin is False
    assert p.pode_criar_usuario is False
    assert p.pode_gerar_senha is False
    assert p.pode_pausar is False
    assert p.pode_mover_equipe is False
    assert p.pode_gerir_equipes is False
    assert p.admin_global is False


def test_admin_read_campos():
    """AdminRead expõe identidade + equipe + flags."""
    r = AdminRead(
        id=1,
        nome="Beltrano",
        matricula="B1",
        guarnicao_id=3,
        is_super_admin=False,
        is_admin=True,
        pode_criar_usuario=True,
        pode_gerar_senha=False,
        pode_pausar=False,
        pode_mover_equipe=False,
        pode_gerir_equipes=False,
        admin_global=False,
    )
    assert r.is_admin is True
    assert r.pode_criar_usuario is True
