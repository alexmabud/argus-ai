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
    op.execute(
        "ALTER TABLE relacionamento_pessoas ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT true"
    )
    op.execute(
        "ALTER TABLE relacionamento_pessoas ADD COLUMN IF NOT EXISTS desativado_em TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE relacionamento_pessoas ADD COLUMN IF NOT EXISTS desativado_por_id INTEGER"
    )
    op.create_index(
        op.f("ix_relacionamento_pessoas_ativo"),
        "relacionamento_pessoas",
        ["ativo"],
        unique=False,
        if_not_exists=True,
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_relacionamento_pessoas_desativado_por_id'
            ) THEN
                ALTER TABLE relacionamento_pessoas
                    ADD CONSTRAINT fk_relacionamento_pessoas_desativado_por_id
                    FOREIGN KEY (desativado_por_id) REFERENCES usuarios(id);
            END IF;
        END $$;
        """
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
