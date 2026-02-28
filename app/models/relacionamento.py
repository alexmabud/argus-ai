"""Modelo de Relacionamento — vínculo entre pessoas abordadas.

Define relacionamentos (associações) materializados entre pessoas
abordadas juntas, com frequência e histórico temporal.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RelacionamentoPessoa(Base, TimestampMixin):
    """Vínculo materializado entre pessoas abordadas juntas.

    Registra quando duas pessoas foram abordadas juntas, com frequência
    de associação e histórico (primeira/última abordagem conjunta).
    Materializar evita queries complexas e permite análise de rede social.

    Attributes:
        id: Identificador único (chave primária).
        pessoa_id_a: ID da pessoa A (FK, CASCADE delete) — sempre < pessoa_id_b.
        pessoa_id_b: ID da pessoa B (FK, CASCADE delete) — sempre > pessoa_id_a.
        frequencia: Número de vezes abordadas juntas (default 1).
        primeira_abordagem_id: ID da primeira abordagem conjunta (FK).
        ultima_abordagem_id: ID da última abordagem conjunta (FK).
        primeira_vez: Timestamp da primeira abordagem conjunta.
        ultima_vez: Timestamp da última abordagem conjunta.
        pessoa_a: Relacionamento com Pessoa (side A).
        pessoa_b: Relacionamento com Pessoa (side B).

    Nota:
        - Constraint: pessoa_id_a < pessoa_id_b evita duplicatas (A-B == B-A).
        - Índice único em (pessoa_id_a, pessoa_id_b).
        - Índice em frequencia para ordenação por força de vínculo.
    """

    __tablename__ = "relacionamento_pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id_a: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    pessoa_id_b: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    frequencia: Mapped[int] = mapped_column(Integer, default=1)
    primeira_abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    ultima_abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    primeira_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultima_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pessoa_a = relationship(
        "Pessoa",
        foreign_keys=[pessoa_id_a],
        back_populates="relacionamentos_como_a",
    )
    pessoa_b = relationship(
        "Pessoa",
        foreign_keys=[pessoa_id_b],
        back_populates="relacionamentos_como_b",
    )

    __table_args__ = (
        UniqueConstraint("pessoa_id_a", "pessoa_id_b", name="uq_relacionamento"),
        CheckConstraint("pessoa_id_a < pessoa_id_b", name="ck_relacionamento_order"),
        Index("idx_relacionamento_freq", "frequencia"),
    )
