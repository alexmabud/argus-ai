"""Mixins e classes base para modelos SQLAlchemy.

Define a classe base DeclarativeBase e mixins para auditoria temporal,
exclusão lógica (soft delete) e isolamento multi-tenant por guarnição.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos ORM.

    Serve como configuração centralizada do SQLAlchemy para todos
    os modelos do sistema, permitindo herança consistente.
    """

    pass


class TimestampMixin:
    """Mixin para campos de auditoria temporal.

    Adiciona campos de timestamp automáticos criado_em e atualizado_em
    em todos os registros, permitindo rastreamento de quando dados foram
    criados e modificados pela última vez.

    Attributes:
        criado_em: Timestamp UTC de criação (auto-preenchido).
        atualizado_em: Timestamp UTC de última atualização (auto-preenchido).
    """

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    """Mixin para exclusão lógica — dados nunca são permanentemente deletados.

    Implementa padrão de soft delete onde registros são marcados como
    inativos em vez de serem removidos do banco. Atende requisitos LGPD
    de rastreabilidade e auditoria, nunca destruindo dados.

    Attributes:
        ativo: Flag booleano indicando se registro está ativo (default True).
        desativado_em: Timestamp UTC de quando foi desativado (null se ativo).
        desativado_por_id: ID do usuário que desativou (referência a Usuario).
    """

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    desativado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    desativado_por_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MultiTenantMixin:
    """Mixin para isolamento por guarnição (multi-tenancy).

    Garante que todos os registros estejam associados a uma guarnição,
    permitindo isolamento de dados entre diferentes unidades operacionais
    e aplicação de filtros automáticos em queries.

    Attributes:
        guarnicao_id: ID da guarnição responsável (chave estrangeira).
    """

    guarnicao_id: Mapped[int] = mapped_column(ForeignKey("guarnicoes.id"), index=True)
