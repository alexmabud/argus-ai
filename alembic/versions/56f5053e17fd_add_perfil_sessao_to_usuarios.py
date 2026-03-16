"""add_perfil_sessao_to_usuarios

Revision ID: 56f5053e17fd
Revises: 48e9ff4bf4be
Create Date: 2026-03-16 13:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "56f5053e17fd"
down_revision: str | None = "48e9ff4bf4be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("posto_graduacao", sa.String(50), nullable=True))
    op.add_column("usuarios", sa.Column("nome_guerra", sa.String(50), nullable=True))
    op.add_column("usuarios", sa.Column("foto_url", sa.String(500), nullable=True))
    op.add_column("usuarios", sa.Column("session_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "session_id")
    op.drop_column("usuarios", "foto_url")
    op.drop_column("usuarios", "nome_guerra")
    op.drop_column("usuarios", "posto_graduacao")
