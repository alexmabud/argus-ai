"""guarnicao_id nullable em todas as tabelas multi-tenant

Torna guarnicao_id opcional (nullable) nas tabelas que usam MultiTenantMixin.
O isolamento multi-tenancy está desativado no modelo de acesso atual, portanto
registros podem existir sem guarnição atribuída.

Tabelas afetadas: pessoas, ocorrencias, veiculos, pessoa_observacoes,
abordagens, vinculos_manuais.

Revision ID: f1a2b3c4d5e6
Revises: 0193ae0cadf6
Create Date: 2026-05-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str = "0193ae0cadf6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELAS = [
    "pessoas",
    "ocorrencias",
    "veiculos",
    "pessoa_observacoes",
    "abordagens",
    "vinculos_manuais",
]


def upgrade() -> None:
    """Torna guarnicao_id nullable em todas as tabelas multi-tenant."""
    for tabela in _TABELAS:
        op.alter_column(
            tabela,
            "guarnicao_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    """Reverte guarnicao_id para NOT NULL (requer que não haja NULLs)."""
    for tabela in reversed(_TABELAS):
        op.alter_column(
            tabela,
            "guarnicao_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
