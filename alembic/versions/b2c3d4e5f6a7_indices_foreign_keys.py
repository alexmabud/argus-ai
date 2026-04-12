"""Migration: índices em foreign keys para performance de JOINs.

Adiciona índices em colunas FK que estavam sem indexação, causando
full table scans em JOINs e queries filtradas.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18 13:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria índices em foreign keys faltantes."""
    op.create_index(op.f("ix_abordagens_usuario_id"), "abordagens", ["usuario_id"], if_not_exists=True)
    op.create_index(op.f("ix_fotos_pessoa_id"), "fotos", ["pessoa_id"], if_not_exists=True)
    op.create_index(op.f("ix_fotos_abordagem_id"), "fotos", ["abordagem_id"], if_not_exists=True)
    op.create_index(op.f("ix_ocorrencias_abordagem_id"), "ocorrencias", ["abordagem_id"], if_not_exists=True)
    op.create_index(op.f("ix_ocorrencias_usuario_id"), "ocorrencias", ["usuario_id"], if_not_exists=True)
    op.create_index(op.f("ix_enderecos_pessoa_pessoa_id"), "enderecos_pessoa", ["pessoa_id"], if_not_exists=True)
    op.create_index(
        op.f("ix_relacionamento_pessoas_primeira_abordagem_id"),
        "relacionamento_pessoas",
        ["primeira_abordagem_id"],
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_relacionamento_pessoas_ultima_abordagem_id"),
        "relacionamento_pessoas",
        ["ultima_abordagem_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove índices de foreign keys."""
    op.drop_index(op.f("ix_relacionamento_pessoas_ultima_abordagem_id"), "relacionamento_pessoas")
    op.drop_index(op.f("ix_relacionamento_pessoas_primeira_abordagem_id"), "relacionamento_pessoas")
    op.drop_index(op.f("ix_enderecos_pessoa_pessoa_id"), "enderecos_pessoa")
    op.drop_index(op.f("ix_ocorrencias_usuario_id"), "ocorrencias")
    op.drop_index(op.f("ix_ocorrencias_abordagem_id"), "ocorrencias")
    op.drop_index(op.f("ix_fotos_abordagem_id"), "fotos")
    op.drop_index(op.f("ix_fotos_pessoa_id"), "fotos")
    op.drop_index(op.f("ix_abordagens_usuario_id"), "abordagens")
