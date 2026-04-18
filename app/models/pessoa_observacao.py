"""Modelo de PessoaObservacao — observações livres vinculadas a uma pessoa.

Registra anotações operacionais sobre uma pessoa abordada, com histórico
cronológico e soft delete para rastreabilidade completa.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class PessoaObservacao(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Observação livre vinculada a uma pessoa.

    Registra anotações operacionais com histórico cronológico. Implementa
    soft delete para nunca perder dados (LGPD), multi-tenancy por guarnição
    e audit log em todas as mutações.

    Attributes:
        id: Identificador único.
        pessoa_id: ID da pessoa dona da observação.
        texto: Conteúdo da observação.
        guarnicao_id: Guarnição (herdado de MultiTenantMixin).
    """

    __tablename__ = "pessoa_observacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"), index=True)
    texto: Mapped[str] = mapped_column(Text)

    # lazy="selectin" evita MissingGreenlet em contexto async (padrão VinculoManual)
    pessoa = relationship("Pessoa", back_populates="observacoes_lista", lazy="selectin")
