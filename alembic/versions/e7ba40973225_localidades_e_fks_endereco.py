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
    # Cria tabela localidades se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS localidades (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            nome_exibicao VARCHAR(200) NOT NULL,
            tipo VARCHAR(10) NOT NULL,
            sigla VARCHAR(2),
            parent_id INTEGER REFERENCES localidades(id),
            ativo BOOLEAN NOT NULL DEFAULT true,
            desativado_em TIMESTAMPTZ,
            desativado_por_id INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_localidades_tipo CHECK (tipo IN ('estado', 'cidade', 'bairro'))
        )
    """)
    op.create_index("ix_localidades_nome", "localidades", ["nome"], if_not_exists=True)
    op.create_index("ix_localidades_parent_id", "localidades", ["parent_id"], if_not_exists=True)
    op.create_index(
        "ix_localidades_tipo_parent_nome", "localidades", ["tipo", "parent_id", "nome"],
        if_not_exists=True,
    )

    # FK columns em enderecos_pessoa (IF NOT EXISTS)
    op.execute("ALTER TABLE enderecos_pessoa ADD COLUMN IF NOT EXISTS estado_id INTEGER")
    op.execute("ALTER TABLE enderecos_pessoa ADD COLUMN IF NOT EXISTS cidade_id INTEGER")
    op.execute("ALTER TABLE enderecos_pessoa ADD COLUMN IF NOT EXISTS bairro_id INTEGER")

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_enderecos_estado') THEN
                ALTER TABLE enderecos_pessoa
                    ADD CONSTRAINT fk_enderecos_estado FOREIGN KEY (estado_id) REFERENCES localidades(id);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_enderecos_cidade') THEN
                ALTER TABLE enderecos_pessoa
                    ADD CONSTRAINT fk_enderecos_cidade FOREIGN KEY (cidade_id) REFERENCES localidades(id);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_enderecos_bairro') THEN
                ALTER TABLE enderecos_pessoa
                    ADD CONSTRAINT fk_enderecos_bairro FOREIGN KEY (bairro_id) REFERENCES localidades(id);
            END IF;
        END $$;
    """)

    # Seed 27 estados (idempotente via ON CONFLICT DO NOTHING na sigla)
    for nome, exibicao, sigla in ESTADOS:
        op.execute(
            sa.text(
                "INSERT INTO localidades (nome, nome_exibicao, tipo, sigla, parent_id, ativo)"
                " SELECT :nome, :exibicao, 'estado', :sigla, NULL, true"
                " WHERE NOT EXISTS (SELECT 1 FROM localidades WHERE sigla = :sigla AND tipo = 'estado')"
            ).bindparams(nome=nome, exibicao=exibicao, sigla=sigla)
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
