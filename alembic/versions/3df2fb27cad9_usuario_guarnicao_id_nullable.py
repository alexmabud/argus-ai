"""usuario: guarnicao_id nullable

Torna o campo guarnicao_id da tabela usuarios nullable para permitir usuários
sem guarnição atribuída (ex: admin global). Endpoints que requerem guarnição
devem verificar e retornar 403 quando o campo for nulo.

Revision ID: 3df2fb27cad9
Revises: 45215d6a95a6
Create Date: 2026-04-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3df2fb27cad9"
down_revision: str = "45215d6a95a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Torna guarnicao_id nullable em usuarios."""
    op.alter_column(
        "usuarios",
        "guarnicao_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Reverte guarnicao_id para NOT NULL (requer que não haja NULLs)."""
    op.alter_column(
        "usuarios",
        "guarnicao_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
