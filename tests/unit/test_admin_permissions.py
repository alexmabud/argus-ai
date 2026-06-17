"""Testes unitários das dependencies de permissão/scope do admin."""

import types

import pytest

from app.api.v1.admin import require_permissao, require_super_admin
from app.core.exceptions import AcessoNegadoError
from app.core.permissions import assert_scope


def _fake_user(**kw):
    """Cria um usuário falso (SimpleNamespace) com flags padrão de menor privilégio.

    Args:
        **kw: Sobrescreve flags individuais.

    Returns:
        SimpleNamespace com os atributos de permissão.
    """
    base = dict(
        id=1,
        is_super_admin=False,
        is_admin=False,
        pode_criar_usuario=False,
        admin_global=False,
        guarnicao_id=1,
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_require_super_admin_bloqueia_delegado():
    with pytest.raises(AcessoNegadoError):
        require_super_admin(_fake_user(is_admin=True))


def test_require_super_admin_passa_dono():
    u = _fake_user(is_super_admin=True)
    assert require_super_admin(u) is u


def test_require_permissao_super_admin_sempre_passa():
    dep = require_permissao("criar_usuario")
    u = _fake_user(is_super_admin=True)
    assert dep(u) is u


def test_require_permissao_delegado_com_flag_passa():
    dep = require_permissao("criar_usuario")
    u = _fake_user(is_admin=True, pode_criar_usuario=True)
    assert dep(u) is u


def test_require_permissao_delegado_sem_flag_bloqueia():
    dep = require_permissao("criar_usuario")
    with pytest.raises(AcessoNegadoError):
        dep(_fake_user(is_admin=True, pode_criar_usuario=False))


def test_assert_scope_super_admin_passa_qualquer_equipe():
    # super-admin com guarnição 1 age sobre a guarnição 99
    assert assert_scope(_fake_user(is_super_admin=True, guarnicao_id=1), 99) is None


def test_assert_scope_global_passa_qualquer_equipe():
    assert assert_scope(_fake_user(is_admin=True, admin_global=True, guarnicao_id=1), 99) is None


def test_assert_scope_delegado_local_mesma_equipe_passa():
    assert assert_scope(_fake_user(is_admin=True, guarnicao_id=5), 5) is None


def test_assert_scope_delegado_local_outra_equipe_bloqueia():
    with pytest.raises(AcessoNegadoError):
        assert_scope(_fake_user(is_admin=True, guarnicao_id=5), 7)


def test_assert_scope_delegado_sem_equipe_bloqueia():
    with pytest.raises(AcessoNegadoError):
        assert_scope(_fake_user(is_admin=True, guarnicao_id=None), None)
