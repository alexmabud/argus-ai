"""uppercase nome de usuario

Converte para MAIÚSCULAS o nome completo e o nome de guerra dos usuários
(policiais) já cadastrados, alinhando ao padrão aplicado nos schemas.
Não toca matrícula, e-mail, senha nem posto_graduacao (lista fixa).

Revision ID: 6531e2eeac14
Revises: 31f2875a7047
Create Date: 2026-06-01 12:52:01.463132

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6531e2eeac14"
down_revision: str | None = "31f2875a7047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CAMPOS: list[tuple[str, str]] = [
    ("usuarios", "nome"),
    ("usuarios", "nome_guerra"),
]


def upgrade() -> None:
    """Converte nome e nome_guerra dos usuários para MAIÚSCULAS."""
    for tabela, coluna in _CAMPOS:
        op.execute(f"UPDATE {tabela} SET {coluna} = UPPER({coluna}) WHERE {coluna} IS NOT NULL")


def downgrade() -> None:
    """Sem volta: o case original não é recuperável."""
    pass
