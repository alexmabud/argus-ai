"""usuario tentativas_falhas e bloqueado_ate

Revision ID: c3d4e5f6a8b9
Revises: b2c3d4e5f6a8
Create Date: 2026-05-26 12:10:00.000000

Adiciona campos para account lockout temporario apos N falhas consecutivas.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a8b9"
down_revision: str = "b2c3d4e5f6a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "tentativas_falhas",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "bloqueado_ate",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "bloqueado_ate")
    op.drop_column("usuarios", "tentativas_falhas")
