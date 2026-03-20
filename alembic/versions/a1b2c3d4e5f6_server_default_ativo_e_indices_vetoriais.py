"""Migration: server_default ativo + índices vetoriais.

Adiciona server_default='true' em todas as colunas `ativo` (SoftDeleteMixin)
para que inserts via SQL puro/migrations tenham ativo=True automaticamente.
Cria índices HNSW para colunas de embedding vetorial (pgvector) para evitar
full table scans em buscas por similaridade.

Revision ID: a1b2c3d4e5f6
Revises: 56f5053e17fd
Create Date: 2026-03-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str = "56f5053e17fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tabelas que usam SoftDeleteMixin (campo ativo).
_TABELAS_COM_ATIVO = [
    "guarnicoes",
    "legislacoes",
    "pessoas",
    "usuarios",
    "veiculos",
    "abordagens",
    "enderecos_pessoa",
    "fotos",
    "ocorrencias",
]


def upgrade() -> None:
    """Adiciona server_default em ativo e cria índices vetoriais HNSW."""
    # A14: server_default para campo ativo em todas as tabelas SoftDeleteMixin
    for tabela in _TABELAS_COM_ATIVO:
        op.alter_column(
            tabela,
            "ativo",
            server_default=sa.text("true"),
        )

    # A15: Índices HNSW para busca vetorial por similaridade cosseno
    # HNSW é mais adequado que IVFFlat para datasets < 1M rows (melhor recall)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fotos_embedding_face_hnsw "
        "ON fotos USING hnsw (embedding_face vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ocorrencias_embedding_hnsw "
        "ON ocorrencias USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """Remove índices vetoriais e server_default do campo ativo."""
    op.execute("DROP INDEX IF EXISTS idx_ocorrencias_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_fotos_embedding_face_hnsw")

    for tabela in _TABELAS_COM_ATIVO:
        op.alter_column(
            tabela,
            "ativo",
            server_default=None,
        )
