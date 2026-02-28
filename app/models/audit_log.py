"""Modelo de Audit Log — registro imutável de ações do sistema.

Define o log de auditoria que rastreia todas as ações para atender
requisitos LGPD de rastreabilidade: quem, o quê, quando e de onde.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Log imutável de todas as ações no sistema.

    Cada ação (CREATE, READ, UPDATE, DELETE, LOGIN, EXPORT, SEARCH, SYNC)
    é registrada com contexto completo: usuário, recurso, timestamp,
    IP, user-agent e detalhes JSON. Nunca é modificado ou deletado,
    atendendo requisitos de rastreabilidade LGPD.

    Attributes:
        id: Identificador único (chave primária).
        timestamp: Data/hora UTC da ação (indexado, padrão: agora).
        usuario_id: ID do usuário que executou a ação (FK).
        acao: Tipo de ação (CREATE, READ, UPDATE, DELETE, LOGIN, EXPORT, SEARCH, SYNC).
        recurso: Tipo de recurso afetado (ex: "pessoa", "abordagem").
        recurso_id: ID do recurso afetado (null para ações de read/search).
        detalhes: JSON com campos alterados, query executada, etc.
        ip_address: IP da requisição.
        user_agent: User-agent da requisição.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    acao: Mapped[str] = mapped_column(String(50), index=True)
    # CREATE, READ, UPDATE, DELETE, LOGIN, EXPORT, SEARCH, SYNC
    recurso: Mapped[str] = mapped_column(String(100))  # ex: "pessoa", "abordagem"
    recurso_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON com campos alterados, query executada etc.
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
