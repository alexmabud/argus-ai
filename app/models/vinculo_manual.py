"""Modelo de VinculoManual — vínculo entre pessoas cadastrado manualmente.

Define relacionamentos manuais entre pessoas, registrados pelo operador
com tipo (ex: 'Irmão') e descrição opcional, independente de abordagens.
"""

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class VinculoManual(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Vínculo manual entre duas pessoas, cadastrado pelo operador.

    Registra relacionamentos conhecidos operacionalmente que não constam
    em abordagens. Diferente de RelacionamentoPessoa, não tem direção
    forçada (A→B e B→A são registros distintos e ambos permitidos).

    Attributes:
        id: Identificador único.
        pessoa_id: ID da pessoa dona do vínculo (quem está sendo visualizado).
        pessoa_vinculada_id: ID da pessoa vinculada.
        tipo: Tipo do vínculo — palavra curta obrigatória (ex: 'Irmão').
        descricao: Detalhe livre opcional (ex: 'Traficando junto na casa ao lado').
        guarnicao_id: Guarnição (herdado de MultiTenantMixin).

    Nota:
        - UNIQUE(pessoa_id, pessoa_vinculada_id) evita duplicatas.
        - CHECK(pessoa_id != pessoa_vinculada_id) impede auto-vínculo.
        - Soft delete via SoftDeleteMixin (ativo, desativado_em, desativado_por_id).
    """

    __tablename__ = "vinculos_manuais"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"), index=True)
    pessoa_vinculada_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    pessoa = relationship(
        "Pessoa",
        foreign_keys=[pessoa_id],
        back_populates="vinculos_manuais",
    )
    # lazy="selectin" é obrigatório: o router acessa .pessoa_vinculada.nome
    # e .foto_principal_url em contexto async — sem selectin causaria MissingGreenlet.
    pessoa_vinculada = relationship(
        "Pessoa",
        foreign_keys=[pessoa_vinculada_id],
        lazy="selectin",
    )

    __table_args__ = (
        # Constraint padrão sem filtro ativo — consistente com RelacionamentoPessoa.
        # Registro soft-deleted mantém o slot único (comportamento intencional:
        # vínculo excluído não deve ser recriado silenciosamente).
        # pessoa_id e pessoa_vinculada_id são PKs globais (não por tenant),
        # portanto UNIQUE(pessoa_id, pessoa_vinculada_id) é naturalmente
        # tenant-scoped sem incluir guarnicao_id.
        UniqueConstraint("pessoa_id", "pessoa_vinculada_id", name="uq_vinculo_manual"),
        CheckConstraint("pessoa_id != pessoa_vinculada_id", name="ck_vinculo_manual_diferente"),
        # Índices explícitos além dos gerados por index=True nos campos.
        # guarnicao_id já é indexado pelo MultiTenantMixin via index=True.
        Index("idx_vinculo_manual_pessoa", "pessoa_id"),
        Index("idx_vinculo_manual_vinculada", "pessoa_vinculada_id"),
    )
