"""add nome_mae em pessoa

Revision ID: a133a5b5dac8
Revises: 2b532a309319
Create Date: 2026-04-17 21:58:37.485091

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a133a5b5dac8"
down_revision: str = "2b532a309319"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna nome_mae em pessoas com indices GIN trgm e btree."""
    op.execute(
        "ALTER TABLE pessoas ADD COLUMN IF NOT EXISTS nome_mae VARCHAR(300)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pessoa_nome_mae_trgm "
        "ON pessoas USING gin (nome_mae gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pessoas_nome_mae ON pessoas (nome_mae)"
    )


def downgrade() -> None:
    """Remove indices e coluna nome_mae em pessoas."""
    op.execute("DROP INDEX IF EXISTS ix_pessoas_nome_mae")
    op.execute("DROP INDEX IF EXISTS idx_pessoa_nome_mae_trgm")
    op.execute("ALTER TABLE pessoas DROP COLUMN IF EXISTS nome_mae")
