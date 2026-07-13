"""add client_id em pessoas e veiculos para dedup sync offline

Revision ID: 599854985e28
Revises: 9a9e5535d7b3
Create Date: 2026-07-13 17:49:51.582241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '599854985e28'
down_revision: Union[str, None] = '9a9e5535d7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pessoas', sa.Column('client_id', sa.String(length=100), nullable=True))
    op.create_index('idx_pessoa_client_id', 'pessoas', ['client_id'], unique=True, postgresql_where='client_id IS NOT NULL')
    op.add_column('veiculos', sa.Column('client_id', sa.String(length=100), nullable=True))
    op.create_index('idx_veiculo_client_id', 'veiculos', ['client_id'], unique=True, postgresql_where='client_id IS NOT NULL')


def downgrade() -> None:
    op.drop_index('idx_veiculo_client_id', table_name='veiculos', postgresql_where='client_id IS NOT NULL')
    op.drop_column('veiculos', 'client_id')
    op.drop_index('idx_pessoa_client_id', table_name='pessoas', postgresql_where='client_id IS NOT NULL')
    op.drop_column('pessoas', 'client_id')
