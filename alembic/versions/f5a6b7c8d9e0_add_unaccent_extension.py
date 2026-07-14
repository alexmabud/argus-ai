"""add unaccent extension

Revision ID: f5a6b7c8d9e0
Revises: e1f2a3b4c5d6
Create Date: 2026-03-25 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    # Neutralizado (achado #27/2026-07-13): busca fuzzy de nome/nome_mãe
    # (pessoa_repo.search_by_nome) usa func.unaccent() extensivamente.
    # DROP EXTENSION teria sucesso "silencioso" na hora (Postgres não rastreia
    # chamadas de função em queries como dependência de DDL) e só quebraria
    # depois, na próxima busca por nome, com "function unaccent(text) does
    # not exist" — falha diferida, difícil de conectar de volta ao downgrade
    # que a causou.
    raise NotImplementedError(
        "Downgrade de f5a6b7c8d9e0 (unaccent) foi desativado de propósito: "
        "dropar a extensão não quebra nada na hora, mas derruba toda busca "
        "fuzzy de nome (pessoa_repo.search_by_nome) na próxima query. Se "
        "precisar mesmo reverter, avalie manualmente se algo depende de "
        "unaccent antes de rodar DROP EXTENSION à mão (achado #27, code "
        "review de segurança 2026-07-13)."
    )
