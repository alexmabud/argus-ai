"""add_bpm_table_and_bpm_id_to_guarnicoes

Revision ID: 0193ae0cadf6
Revises: ac82533aca4d
Create Date: 2026-05-03 12:25:21.205019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0193ae0cadf6'
down_revision: Union[str, None] = 'ac82533aca4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela bpm, migra dados de unidade para bpm_id, remove coluna unidade."""
    # 1. Criar tabela bpm (sem FK, para evitar dependência circular em criação)
    op.create_table(
        "bpm",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("desativado_por_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )

    # 1b. FK desativado_por_id -> usuarios.id (criada separadamente)
    op.create_foreign_key(
        "fk_bpm_desativado_por_id",
        "bpm", "usuarios",
        ["desativado_por_id"], ["id"],
    )

    # 2. Inserir BPMs a partir dos valores únicos de guarnicoes.unidade
    op.execute("""
        INSERT INTO bpm (nome, ativo, criado_em, atualizado_em)
        SELECT DISTINCT unidade, true, now(), now()
        FROM guarnicoes
        WHERE ativo = true AND unidade IS NOT NULL AND unidade != ''
    """)

    # 3. Adicionar bpm_id como nullable (para preencher antes de NOT NULL)
    op.add_column("guarnicoes", sa.Column("bpm_id", sa.Integer(), nullable=True))

    # 4. FK constraint
    op.create_foreign_key(
        "fk_guarnicoes_bpm_id",
        "guarnicoes", "bpm",
        ["bpm_id"], ["id"],
    )

    # 5. Mapear cada guarnicao para seu BPM pelo valor de unidade
    op.execute("""
        UPDATE guarnicoes g
        SET bpm_id = b.id
        FROM bpm b
        WHERE b.nome = g.unidade
    """)

    # 6. Index em bpm_id
    op.create_index("ix_guarnicoes_bpm_id", "guarnicoes", ["bpm_id"])

    # 7. Tornar bpm_id NOT NULL
    op.alter_column("guarnicoes", "bpm_id", nullable=False)

    # 8. Remover coluna unidade
    op.drop_column("guarnicoes", "unidade")


def downgrade() -> None:
    """Reverte: restaura coluna unidade, remove bpm_id, remove tabela bpm."""
    # Recriar unidade como nullable
    op.add_column("guarnicoes", sa.Column("unidade", sa.String(200), nullable=True))

    # Restaurar valores de unidade a partir do bpm
    op.execute("""
        UPDATE guarnicoes g
        SET unidade = b.nome
        FROM bpm b
        WHERE b.id = g.bpm_id
    """)

    # Tornar unidade NOT NULL
    op.alter_column("guarnicoes", "unidade", nullable=False)

    # Remover bpm_id
    op.drop_index("ix_guarnicoes_bpm_id", table_name="guarnicoes")
    op.drop_constraint("fk_guarnicoes_bpm_id", "guarnicoes", type_="foreignkey")
    op.drop_column("guarnicoes", "bpm_id")

    # Remover tabela bpm (FK desativado_por_id usa use_alter)
    op.drop_constraint("fk_bpm_desativado_por_id", "bpm", type_="foreignkey")
    op.drop_table("bpm")
