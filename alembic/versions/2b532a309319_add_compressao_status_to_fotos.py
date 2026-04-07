"""fotos: adicionar campo compressao_status

Adiciona o campo compressao_status à tabela fotos para rastrear o estado
da compressão de cada foto (ex: 'na', 'pending', 'done', 'error').
Valor padrão 'na' indica que compressão não se aplica ou ainda não foi processada.

Revision ID: 2b532a309319
Revises: 45215d6a95a6
Create Date: 2026-04-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b532a309319"
down_revision: str | None = "45215d6a95a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna compressao_status na tabela fotos."""
    op.add_column(
        "fotos",
        sa.Column(
            "compressao_status",
            sa.String(length=10),
            server_default="na",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove coluna compressao_status da tabela fotos."""
    op.drop_column("fotos", "compressao_status")
