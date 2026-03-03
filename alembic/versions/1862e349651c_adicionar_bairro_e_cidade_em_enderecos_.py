"""adicionar bairro e cidade em enderecos_pessoa

Revision ID: 1862e349651c
Revises: 9a79fc5e1da2
Create Date: 2026-03-03 10:56:58.779626

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1862e349651c"
down_revision: str | None = "9a79fc5e1da2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("enderecos_pessoa", sa.Column("bairro", sa.String(length=200), nullable=True))
    op.add_column("enderecos_pessoa", sa.Column("cidade", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("enderecos_pessoa", "cidade")
    op.drop_column("enderecos_pessoa", "bairro")
