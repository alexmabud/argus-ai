"""Testes dos schemas Pydantic de Pessoa para o campo nome_mae.

Valida que os schemas PessoaCreate e PessoaUpdate aceitam o novo campo
opcional nome_mae, respeitando o limite de 300 caracteres.
"""

from app.schemas.pessoa import PessoaCreate, PessoaUpdate


def test_pessoa_create_aceita_nome_mae():
    p = PessoaCreate(nome="Fulano", nome_mae="Maria")
    assert p.nome_mae == "Maria"


def test_pessoa_create_nome_mae_opcional():
    p = PessoaCreate(nome="Fulano")
    assert p.nome_mae is None


def test_pessoa_create_nome_mae_max_length():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PessoaCreate(nome="Fulano", nome_mae="x" * 301)


def test_pessoa_update_aceita_nome_mae():
    p = PessoaUpdate(nome_mae="Nova Mae")
    assert p.nome_mae == "Nova Mae"
