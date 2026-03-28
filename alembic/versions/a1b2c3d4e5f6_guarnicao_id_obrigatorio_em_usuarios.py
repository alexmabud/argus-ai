"""guarnicao_id obrigatorio em usuarios

Todo usuário pertence a uma guarnição. Reflete a regra de negócio atual
onde existe uma única guarnição genérica e todos os usuários são vinculados
a ela. Remove o nullable=True que foi adicionado anteriormente.

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-03-28

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "usuarios",
        "guarnicao_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "usuarios",
        "guarnicao_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
