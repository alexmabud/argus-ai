"""Adicionar soft delete em relacionamento_pessoas.

A tabela relacionamento_pessoas foi criada sem as colunas de soft delete
(ativo, desativado_em, desativado_por_id) que fazem parte do SoftDeleteMixin.
Esta migration corrige a inconsistência entre o model e o schema do banco.

Revision ID: e1f2a3b4c5d6
Revises: c3d4e5f6a7b8
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona colunas de soft delete na tabela relacionamento_pessoas."""
    op.add_column(
        "relacionamento_pessoas",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "relacionamento_pessoas",
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relacionamento_pessoas",
        sa.Column("desativado_por_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_relacionamento_pessoas_ativo"),
        "relacionamento_pessoas",
        ["ativo"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_relacionamento_pessoas_desativado_por_id",
        "relacionamento_pessoas",
        "usuarios",
        ["desativado_por_id"],
        ["id"],
        use_alter=True,
    )


def downgrade() -> None:
    """Remove colunas de soft delete da tabela relacionamento_pessoas."""
    op.drop_constraint(
        "fk_relacionamento_pessoas_desativado_por_id",
        "relacionamento_pessoas",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_relacionamento_pessoas_ativo"),
        table_name="relacionamento_pessoas",
    )
    op.drop_column("relacionamento_pessoas", "desativado_por_id")
    op.drop_column("relacionamento_pessoas", "desativado_em")
    op.drop_column("relacionamento_pessoas", "ativo")
