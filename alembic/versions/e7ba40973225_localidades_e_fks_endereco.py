"""localidades_e_fks_endereco

Revision ID: e7ba40973225
Revises: f5a6b7c8d9e0
Create Date: 2026-03-31 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7ba40973225"
down_revision: str = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ESTADOS = [
    ("acre", "Acre", "AC"),
    ("alagoas", "Alagoas", "AL"),
    ("amapa", "Amapá", "AP"),
    ("amazonas", "Amazonas", "AM"),
    ("bahia", "Bahia", "BA"),
    ("ceara", "Ceará", "CE"),
    ("distrito federal", "Distrito Federal", "DF"),
    ("espirito santo", "Espírito Santo", "ES"),
    ("goias", "Goiás", "GO"),
    ("maranhao", "Maranhão", "MA"),
    ("mato grosso", "Mato Grosso", "MT"),
    ("mato grosso do sul", "Mato Grosso do Sul", "MS"),
    ("minas gerais", "Minas Gerais", "MG"),
    ("para", "Pará", "PA"),
    ("paraiba", "Paraíba", "PB"),
    ("parana", "Paraná", "PR"),
    ("pernambuco", "Pernambuco", "PE"),
    ("piaui", "Piauí", "PI"),
    ("rio de janeiro", "Rio de Janeiro", "RJ"),
    ("rio grande do norte", "Rio Grande do Norte", "RN"),
    ("rio grande do sul", "Rio Grande do Sul", "RS"),
    ("rondonia", "Rondônia", "RO"),
    ("roraima", "Roraima", "RR"),
    ("santa catarina", "Santa Catarina", "SC"),
    ("sao paulo", "São Paulo", "SP"),
    ("sergipe", "Sergipe", "SE"),
    ("tocantins", "Tocantins", "TO"),
]


def upgrade() -> None:
    """Cria tabela localidades, adiciona FKs em enderecos_pessoa e seed dos 27 estados."""
    op.create_table(
        "localidades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("nome_exibicao", sa.String(length=200), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("sigla", sa.String(length=2), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desativado_por_id", sa.Integer(), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("tipo IN ('estado', 'cidade', 'bairro')", name="ck_localidades_tipo"),
        sa.ForeignKeyConstraint(["parent_id"], ["localidades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_localidades_nome", "localidades", ["nome"])
    op.create_index("ix_localidades_parent_id", "localidades", ["parent_id"])
    op.create_index("ix_localidades_tipo_parent_nome", "localidades", ["tipo", "parent_id", "nome"])

    # FK columns em enderecos_pessoa
    op.add_column("enderecos_pessoa", sa.Column("estado_id", sa.Integer(), nullable=True))
    op.add_column("enderecos_pessoa", sa.Column("cidade_id", sa.Integer(), nullable=True))
    op.add_column("enderecos_pessoa", sa.Column("bairro_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_enderecos_estado", "enderecos_pessoa", "localidades", ["estado_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_enderecos_cidade", "enderecos_pessoa", "localidades", ["cidade_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_enderecos_bairro", "enderecos_pessoa", "localidades", ["bairro_id"], ["id"]
    )

    # Seed 27 estados
    localidades_table = sa.table(
        "localidades",
        sa.column("nome", sa.String),
        sa.column("nome_exibicao", sa.String),
        sa.column("tipo", sa.String),
        sa.column("sigla", sa.String),
        sa.column("parent_id", sa.Integer),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(
        localidades_table,
        [
            {
                "nome": nome,
                "nome_exibicao": exibicao,
                "tipo": "estado",
                "sigla": sigla,
                "parent_id": None,
                "ativo": True,
            }
            for nome, exibicao, sigla in ESTADOS
        ],
    )


def downgrade() -> None:
    """Remove FKs de enderecos_pessoa e dropa tabela localidades."""
    op.drop_constraint("fk_enderecos_bairro", "enderecos_pessoa", type_="foreignkey")
    op.drop_constraint("fk_enderecos_cidade", "enderecos_pessoa", type_="foreignkey")
    op.drop_constraint("fk_enderecos_estado", "enderecos_pessoa", type_="foreignkey")
    op.drop_column("enderecos_pessoa", "bairro_id")
    op.drop_column("enderecos_pessoa", "cidade_id")
    op.drop_column("enderecos_pessoa", "estado_id")
    op.drop_index("ix_localidades_tipo_parent_nome", table_name="localidades")
    op.drop_index("ix_localidades_parent_id", table_name="localidades")
    op.drop_index("ix_localidades_nome", table_name="localidades")
    op.drop_table("localidades")
