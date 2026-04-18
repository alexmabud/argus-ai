"""adicionar tabela pessoa_observacoes

Revision ID: eab4eec560e4
Revises: a133a5b5dac8
Create Date: 2026-04-17 23:31:09.312712

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eab4eec560e4"
down_revision: str | None = "a133a5b5dac8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria tabela pessoa_observacoes com índices e chaves estrangeiras."""
    op.create_table(
        "pessoa_observacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desativado_por_id", sa.Integer(), nullable=True),
        sa.Column("guarnicao_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["desativado_por_id"],
            ["usuarios.id"],
            name="fk_pessoa_observacoes_desativado_por_id",
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(["guarnicao_id"], ["guarnicoes.id"]),
        sa.ForeignKeyConstraint(["pessoa_id"], ["pessoas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pessoa_observacoes_ativo", "pessoa_observacoes", ["ativo"], unique=False
    )
    op.create_index(
        "ix_pessoa_observacoes_guarnicao_id",
        "pessoa_observacoes",
        ["guarnicao_id"],
        unique=False,
    )
    op.create_index(
        "ix_pessoa_observacoes_pessoa_id",
        "pessoa_observacoes",
        ["pessoa_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove tabela pessoa_observacoes e seus índices."""
    op.drop_index("ix_pessoa_observacoes_pessoa_id", table_name="pessoa_observacoes")
    op.drop_index(
        "ix_pessoa_observacoes_guarnicao_id", table_name="pessoa_observacoes"
    )
    op.drop_index("ix_pessoa_observacoes_ativo", table_name="pessoa_observacoes")
    op.drop_table("pessoa_observacoes")
