"""uppercase dados existentes

Converte para MAIÚSCULAS os campos de texto digitados pelo usuário já
gravados no banco, alinhando os dados antigos ao novo padrão aplicado nos
schemas Pydantic. Não toca campos criptografados (cpf), datas, coordenadas
nem dados de usuário (email/senha/login).

O UPPER() do PostgreSQL é locale-aware (UTF-8) e respeita acentos
(ex: "joão" -> "JOÃO").

Revision ID: 31f2875a7047
Revises: c3d4e5f6a8b9
Create Date: 2026-06-01 11:09:10.638634

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "31f2875a7047"
down_revision: str | None = "c3d4e5f6a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (tabela, coluna) de texto livre a normalizar para MAIÚSCULAS.
_CAMPOS: list[tuple[str, str]] = [
    ("pessoas", "nome"),
    ("pessoas", "apelido"),
    ("pessoas", "nome_mae"),
    ("pessoas", "observacoes"),
    ("pessoa_observacoes", "texto"),
    ("enderecos_pessoa", "endereco"),
    ("enderecos_pessoa", "bairro"),
    ("enderecos_pessoa", "cidade"),
    ("enderecos_pessoa", "estado"),
    ("abordagens", "endereco_texto"),
    ("abordagens", "observacao"),
    ("veiculos", "modelo"),
    ("veiculos", "cor"),
    ("veiculos", "tipo"),
    ("veiculos", "observacoes"),
]


def upgrade() -> None:
    """Converte os campos de texto existentes para MAIÚSCULAS."""
    for tabela, coluna in _CAMPOS:
        op.execute(
            f"UPDATE {tabela} SET {coluna} = UPPER({coluna}) "
            f"WHERE {coluna} IS NOT NULL"
        )


def downgrade() -> None:
    """Sem volta: o case (maiúsc./minúsc.) original não é recuperável."""
    pass
