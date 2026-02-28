"""Modelo de Guarnição — unidade operacional do sistema.

Define a entidade central de multi-tenancy, representando uma
unidade policial ou guarnição que contém membros e dados operacionais.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    """Unidade operacional que isola dados entre guarnições.

    Representa uma guarnição, companhia ou unidade policial que usa o sistema.
    Todos os dados operacionais (abordagens, pessoas, ocorrências) estão
    isolados por guarnicao_id, garantindo multi-tenancy.

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome descritivo (ex: "3ª Cia - GU 01").
        unidade: Unidade administrativa superior (ex: "3º BPM").
        codigo: Código único para identificação (ex: "3BPM-3CIA-GU01").
        membros: Relacionamento com usuários (oficiais) da guarnição.
    """

    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))  # ex: "3ª Cia - GU 01"
    unidade: Mapped[str] = mapped_column(String(200))  # ex: "3º BPM"
    codigo: Mapped[str] = mapped_column(String(50), unique=True)  # ex: "3BPM-3CIA-GU01"

    membros = relationship("Usuario", back_populates="guarnicao")
