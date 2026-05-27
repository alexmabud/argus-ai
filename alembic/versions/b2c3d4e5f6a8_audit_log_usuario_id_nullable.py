"""audit_log usuario_id nullable

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-05-26 12:00:00.000000

Permite usuario_id NULL em audit_logs para eventos sem usuario associado
(ex: LOGIN_FAILED com matricula inexistente).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a8"
down_revision: str = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "usuario_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "usuario_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
