"""add_isolamento_abordagens_em_guarnicoes

Adiciona coluna isolamento_abordagens em guarnicoes.
Quando True, membros da equipe veem apenas abordagens da própria equipe.
Quando False (padrão), veem todas as abordagens do sistema.

Revision ID: ac82533aca4d
Revises: eab4eec560e4
Create Date: 2026-04-30 20:17:37.767243

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac82533aca4d"
down_revision: str | None = "eab4eec560e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna isolamento_abordagens em guarnicoes (default False)."""
    op.add_column(
        "guarnicoes",
        sa.Column(
            "isolamento_abordagens",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove a coluna isolamento_abordagens."""
    op.drop_column("guarnicoes", "isolamento_abordagens")
