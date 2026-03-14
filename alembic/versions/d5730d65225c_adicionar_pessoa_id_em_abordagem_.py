"""adicionar pessoa_id em abordagem_veiculos

Revision ID: d5730d65225c
Revises: 7e93f610776f
Create Date: 2026-03-14 11:40:52.684073

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5730d65225c"
down_revision: str | None = "7e93f610776f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "abordagem_veiculos",
        sa.Column(
            "pessoa_id",
            sa.Integer(),
            sa.ForeignKey("pessoas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_abordagem_veiculo_pessoa",
        "abordagem_veiculos",
        ["pessoa_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_abordagem_veiculo_pessoa", table_name="abordagem_veiculos")
    op.drop_column("abordagem_veiculos", "pessoa_id")
