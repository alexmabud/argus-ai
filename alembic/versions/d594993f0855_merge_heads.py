"""merge_heads

Revision ID: d594993f0855
Revises: 1ab2b1fc05fc, 4f6309edf92f
Create Date: 2026-03-09 12:51:40.480095

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d594993f0855"
down_revision: str | None = ("1ab2b1fc05fc", "4f6309edf92f")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
