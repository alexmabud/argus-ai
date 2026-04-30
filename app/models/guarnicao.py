"""Modelo de Guarnição (Equipe) — unidade operacional do sistema.

Define a entidade central de multi-tenancy, representando uma equipe policial
que contém membros e dados operacionais isolados.

NOTA SOBRE NOMENCLATURA: no banco de dados e código interno, a entidade
chama-se "guarnicao" / "guarnicoes". No frontend e para o usuário final,
é exibida como "Equipe". Não há renomeação — apenas labels diferentes na UI.
Manutenções futuras devem manter o nome "guarnicao" no código.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    """Unidade operacional (Equipe) que isola dados entre guarnições.

    Representa uma equipe policial que usa o sistema. Dados operacionais
    (abordagens, pessoas, ocorrências) são associados via guarnicao_id,
    garantindo multi-tenancy. O campo isolamento_abordagens controla se os
    membros da equipe veem apenas as abordagens próprias (True) ou todas as
    abordagens do sistema (False, padrão).

    Pessoas abordadas são sempre visíveis para todos, independentemente
    do isolamento (decisão de design).

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome descritivo da equipe (ex: "3ª Cia - GU 01").
        unidade: Unidade administrativa superior (ex: "3º BPM").
        codigo: Código único para identificação (ex: "3BPM-3CIA-GU01").
        isolamento_abordagens: Se True, membros veem apenas abordagens da
            própria equipe. Se False (padrão), veem todas as abordagens.
        membros: Relacionamento com usuários (oficiais) da equipe.
    """

    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    unidade: Mapped[str] = mapped_column(String(200))
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    isolamento_abordagens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    membros = relationship(
        "Usuario",
        back_populates="guarnicao",
        foreign_keys="Usuario.guarnicao_id",
        lazy="selectin",
    )
