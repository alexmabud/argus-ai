"""Migration: audit_log JSONB + guarnicao_id em fotos/enderecos + soft delete em junctions.

Três mudanças de schema:
1. audit_logs.detalhes: Text → JSONB (consultas estruturadas no log de auditoria)
2. fotos/enderecos_pessoa: adiciona guarnicao_id nullable (consistência multi-tenant)
3. abordagem_pessoas/abordagem_veiculos: adiciona colunas SoftDeleteMixin
   (ativo, desativado_em, desativado_por_id) para conformidade LGPD

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica mudanças: JSONB, multi-tenant e soft delete."""
    # 1. audit_logs.detalhes: Text → JSONB
    # Converte dados existentes de texto JSON para JSONB nativo
    op.execute(
        "ALTER TABLE audit_logs " "ALTER COLUMN detalhes TYPE JSONB " "USING detalhes::jsonb"
    )

    # 2. guarnicao_id nullable em fotos e enderecos_pessoa
    op.add_column(
        "fotos",
        sa.Column("guarnicao_id", sa.Integer(), sa.ForeignKey("guarnicoes.id"), nullable=True),
    )
    op.create_index(op.f("ix_fotos_guarnicao_id"), "fotos", ["guarnicao_id"])

    op.add_column(
        "enderecos_pessoa",
        sa.Column("guarnicao_id", sa.Integer(), sa.ForeignKey("guarnicoes.id"), nullable=True),
    )
    op.create_index(op.f("ix_enderecos_pessoa_guarnicao_id"), "enderecos_pessoa", ["guarnicao_id"])

    # 3. SoftDeleteMixin em abordagem_pessoas
    op.add_column(
        "abordagem_pessoas",
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "abordagem_pessoas",
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "abordagem_pessoas",
        sa.Column(
            "desativado_por_id",
            sa.Integer(),
            sa.ForeignKey(
                "usuarios.id", name="fk_abordagem_pessoas_desativado_por_id", use_alter=True
            ),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_abordagem_pessoas_ativo"), "abordagem_pessoas", ["ativo"])

    # 4. SoftDeleteMixin em abordagem_veiculos
    op.add_column(
        "abordagem_veiculos",
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "abordagem_veiculos",
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "abordagem_veiculos",
        sa.Column(
            "desativado_por_id",
            sa.Integer(),
            sa.ForeignKey(
                "usuarios.id", name="fk_abordagem_veiculos_desativado_por_id", use_alter=True
            ),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_abordagem_veiculos_ativo"), "abordagem_veiculos", ["ativo"])


def downgrade() -> None:
    """Reverte mudanças: remove colunas adicionadas e restaura Text."""
    # 4. Remove SoftDeleteMixin de abordagem_veiculos
    op.drop_index(op.f("ix_abordagem_veiculos_ativo"), "abordagem_veiculos")
    op.drop_column("abordagem_veiculos", "desativado_por_id")
    op.drop_column("abordagem_veiculos", "desativado_em")
    op.drop_column("abordagem_veiculos", "ativo")

    # 3. Remove SoftDeleteMixin de abordagem_pessoas
    op.drop_index(op.f("ix_abordagem_pessoas_ativo"), "abordagem_pessoas")
    op.drop_column("abordagem_pessoas", "desativado_por_id")
    op.drop_column("abordagem_pessoas", "desativado_em")
    op.drop_column("abordagem_pessoas", "ativo")

    # 2. Remove guarnicao_id de fotos e enderecos_pessoa
    op.drop_index(op.f("ix_enderecos_pessoa_guarnicao_id"), "enderecos_pessoa")
    op.drop_column("enderecos_pessoa", "guarnicao_id")

    op.drop_index(op.f("ix_fotos_guarnicao_id"), "fotos")
    op.drop_column("fotos", "guarnicao_id")

    # 1. audit_logs.detalhes: JSONB → Text
    op.execute("ALTER TABLE audit_logs " "ALTER COLUMN detalhes TYPE TEXT " "USING detalhes::text")
