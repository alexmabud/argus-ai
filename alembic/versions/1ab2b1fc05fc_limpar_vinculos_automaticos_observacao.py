"""limpar vínculos automáticos do campo observacao

Revision ID: 1ab2b1fc05fc
Revises: 9a79fc5e1da2
Create Date: 2026-03-08 00:00:00.000000

Remove o texto "Vínculos: ..." que era appendado automaticamente pelo frontend
ao campo observacao das abordagens. Esse texto é redundante pois a relação
veiculo↔pessoa já está estruturada nas tabelas abordagem_veiculos e
abordagem_pessoas.

Casos tratados:
  - "Vínculos: BBB2222 → Teste B"           → NULL
  - "Nada encontrado\nVínculos: BBB → X"    → "Nada encontrado"
  - "Texto real"                             → "Texto real" (sem alteração)
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ab2b1fc05fc"
down_revision: str | None = "9a79fc5e1da2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove linhas 'Vínculos:' auto-geradas do campo observacao."""
    op.execute(
        r"""
        UPDATE abordagens
        SET observacao = NULLIF(
            TRIM(
                REGEXP_REPLACE(observacao, E'(\\n)?Vínculos:[^\\n]*', '', 'g')
            ),
            ''
        )
        WHERE observacao LIKE '%Vínculos:%'
    """
    )


def downgrade() -> None:
    """Não há como recuperar os dados removidos."""
    pass
