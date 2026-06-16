"""add admin permissions usuarios

Adiciona is_super_admin e as flags granulares de admin delegado
(pode_criar_usuario, pode_gerar_senha, pode_pausar, pode_mover_equipe,
pode_gerir_equipes, admin_global) à tabela usuarios.

Revision ID: b7c1d2e3f4a5
Revises: a9f77a36acfb
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, None] = 'a9f77a36acfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for col in (
        "is_super_admin",
        "pode_criar_usuario",
        "pode_gerar_senha",
        "pode_pausar",
        "pode_mover_equipe",
        "pode_gerir_equipes",
        "admin_global",
    ):
        op.add_column(
            "usuarios",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    for col in (
        "admin_global",
        "pode_gerir_equipes",
        "pode_mover_equipe",
        "pode_pausar",
        "pode_gerar_senha",
        "pode_criar_usuario",
        "is_super_admin",
    ):
        op.drop_column("usuarios", col)
