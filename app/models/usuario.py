"""Modelo de Usuário — oficial ou membro da guarnição.

Define o usuário (oficial de patrulhamento) do sistema, com autenticação
e permissões associadas à guarnição.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Usuario(Base, TimestampMixin, SoftDeleteMixin):
    """Usuário do sistema — oficial ou membro de guarnição.

    Representa um oficial ou policial que usa o sistema para registrar
    abordagens, consultar dados e gerar ocorrências. Autenticação via
    matrícula e senha_hash (bcrypt). Sempre vinculado a uma guarnição.

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome completo do oficial.
        matricula: Número de matrícula único (indexado para login).
        email: Email do oficial (único, opcional).
        senha_hash: Hash bcrypt da senha (nunca armazenar plain text).
        guarnicao_id: ID da guarnição (chave estrangeira).
        is_admin: Flag indicando permissões administrativas.
        guarnicao: Relacionamento com Guarnicao.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    matricula: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    guarnicao_id: Mapped[int] = mapped_column(ForeignKey("guarnicoes.id"))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    guarnicao = relationship(
        "Guarnicao",
        back_populates="membros",
        foreign_keys=[guarnicao_id],
    )
