"""backfill guarnicao_id em fotos legadas

Migração de dados (sem alteração de schema). Antes da correção em
app/api/v1/fotos.py (upload principal), apenas o endpoint /fotos/midias
persistia guarnicao_id na Foto — fotos vinculadas a pessoa (rosto, corpo,
evidencia etc) ficavam com guarnicao_id NULL. Isso faz com que
TenantFilter.check_ownership negue (403) a desativação dessas fotos via
DELETE /fotos/{id} para usuários não-admin, mesmo sendo da guarnição
correta.

Preenche o guarnicao_id ausente a partir da entidade vinculada, na
ordem: pessoa -> abordagem -> veiculo. Idempotente — só toca linhas com
guarnicao_id IS NULL, seguro para rodar mais de uma vez.

Revision ID: d10f90d496ce
Revises: b7c1d2e3f4a5
Create Date: 2026-07-03 23:16:52.731280

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d10f90d496ce"
down_revision: str | None = "b7c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: SQL do backfill, extraído em constante para ser exercitado em teste
#: (tests/unit/test_migration_backfill_guarnicao_fotos.py) sem depender de
#: um contexto de execução do Alembic.
BACKFILL_GUARNICAO_ID_SQL = """
    UPDATE fotos
    SET guarnicao_id = COALESCE(
        (SELECT p.guarnicao_id FROM pessoas p WHERE p.id = fotos.pessoa_id),
        (SELECT a.guarnicao_id FROM abordagens a WHERE a.id = fotos.abordagem_id),
        (SELECT v.guarnicao_id FROM veiculos v WHERE v.id = fotos.veiculo_id)
    )
    WHERE guarnicao_id IS NULL
"""


def upgrade() -> None:
    """Preenche guarnicao_id de fotos legadas a partir da entidade vinculada."""
    op.execute(BACKFILL_GUARNICAO_ID_SQL)


def downgrade() -> None:
    """Sem volta: não há como distinguir guarnicao_id original de backfill."""
    pass
