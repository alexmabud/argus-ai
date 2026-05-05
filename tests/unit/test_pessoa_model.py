"""Testes do model Pessoa — validação de campos e comportamento básico."""


def test_pessoa_tem_campo_nome_mae():
    """Pessoa deve aceitar nome_mae opcional (nullable)."""
    from app.models.pessoa import Pessoa

    p = Pessoa(nome="Fulano de Tal", nome_mae="Maria das Dores", guarnicao_id=1)
    assert p.nome_mae == "Maria das Dores"

    p2 = Pessoa(nome="Ciclano", guarnicao_id=1)
    assert p2.nome_mae is None


def test_pessoa_guarnicao_id_nullable():
    """guarnicao_id em Pessoa deve ser nullable (multi-tenancy desativado)."""
    from sqlalchemy import inspect as sa_inspect

    from app.models.pessoa import Pessoa

    col = sa_inspect(Pessoa).columns["guarnicao_id"]
    assert col.nullable is True, "guarnicao_id deve ser nullable na coluna SQLAlchemy"
