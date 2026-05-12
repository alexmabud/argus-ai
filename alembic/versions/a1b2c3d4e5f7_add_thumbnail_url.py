"""add thumbnail_url em fotos e foto_principal_thumb_url em pessoas

Revision ID: a1b2c3d4e5f7
Revises: 8a8a149bf2ce
Create Date: 2026-05-12 12:00:00.000000

Adiciona campo ``thumbnail_url`` em ``fotos`` (caminho relativo
``/storage/...`` da versão reduzida ~300px JPEG) e o paralelo
``foto_principal_thumb_url`` em ``pessoas``. Usado pelas listagens
para evitar baixar fotos cheias quando só o thumbnail é necessário,
reduzindo drasticamente o tráfego do proxy ``/storage``.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str = "8a8a149bf2ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona colunas de thumbnail em fotos e pessoas."""
    op.add_column(
        "fotos",
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "pessoas",
        sa.Column("foto_principal_thumb_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Remove colunas de thumbnail."""
    op.drop_column("pessoas", "foto_principal_thumb_url")
    op.drop_column("fotos", "thumbnail_url")
