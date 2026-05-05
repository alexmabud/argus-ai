"""add_isolamento_abordagens_em_bpms

Revision ID: 8a8a149bf2ce
Revises: f1a2b3c4d5e6
Create Date: 2026-05-05 18:34:02.588161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8a8a149bf2ce'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bpm",
        sa.Column(
            "isolamento_abordagens",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("bpm", "isolamento_abordagens")
