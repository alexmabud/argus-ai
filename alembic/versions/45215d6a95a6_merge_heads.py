"""merge_heads

Revision ID: 45215d6a95a6
Revises: cc1234567890, e7ba40973225
Create Date: 2026-03-31 20:49:45.874583

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "45215d6a95a6"
down_revision: str | None = ("cc1234567890", "e7ba40973225")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
