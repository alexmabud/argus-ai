"""Modelo de Guarnição (Equipe) — unidade operacional do sistema.

Define a entidade central de multi-tenancy, representando uma equipe policial
que contém membros e dados operacionais isolados. Cada equipe pertence a um BPM.

NOTA SOBRE NOMENCLATURA: no banco de dados e código interno, a entidade
chama-se "guarnicao" / "guarnicoes". No frontend e para o usuário final,
é exibida como "Equipe". Não há renomeação — apenas labels diferentes na UI.
Manutenções futuras devem manter o nome "guarnicao" no código.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    """Unidade operacional (Equipe) que isola dados entre guarnições.

    Representa uma equipe policial que usa o sistema. Pertence a um BPM
    (Batalhão de Polícia Militar). O campo isolamento_abordagens controla
    se os membros da equipe veem apenas as abordagens próprias (True) ou
    todas as abordagens do sistema (False, padrão).

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome descritivo da equipe (ex: "3ª Cia - GU 01").
        bpm_id: FK para o BPM ao qual esta equipe pertence.
        codigo: Código único para identificação (ex: "14BPM-3CIA-GU01").
        isolamento_abordagens: Se True, membros veem apenas abordagens da
            própria equipe. Se False (padrão), veem todas as abordagens.
        bpm: Relacionamento com o BPM pai.
        membros: Relacionamento com usuários (oficiais) da equipe.
    """

    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    bpm_id: Mapped[int] = mapped_column(ForeignKey("bpm.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    isolamento_abordagens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    bpm = relationship(
        "Bpm",
        back_populates="guarnicoes",
        lazy="selectin",
    )

    membros = relationship(
        "Usuario",
        back_populates="guarnicao",
        foreign_keys="Usuario.guarnicao_id",
        lazy="selectin",
    )
