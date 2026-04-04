"""Modelo de Usuário — oficial ou membro da guarnição.

Define o usuário (oficial de patrulhamento) do sistema, com autenticação,
perfil (posto, nome de guerra, foto) e controle de sessão exclusiva.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

#: Lista fixa de postos e graduações da Polícia Militar.
POSTOS_GRADUACAO: list[str] = [
    "Soldado",
    "Cabo",
    "3º Sargento",
    "2º Sargento",
    "1º Sargento",
    "Subtenente",
    "Aspirante",
    "2º Tenente",
    "1º Tenente",
    "Capitão",
    "Major",
    "Tenente-Coronel",
    "Coronel",
]


class Usuario(Base, TimestampMixin, SoftDeleteMixin):
    """Usuário do sistema — oficial ou membro de guarnição.

    Representa um oficial ou policial que usa o sistema para registrar
    abordagens, consultar dados e gerar ocorrências. Autenticação via
    matrícula e senha_hash (bcrypt). Sempre vinculado a uma guarnição.

    A segurança de sessão é garantida pelo campo `session_id`: gerado a cada
    login e embutido no JWT. Qualquer nova autenticação invalida sessões anteriores.
    Senhas são sempre geradas pelo admin e consumidas no primeiro uso.

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome completo do oficial.
        matricula: Número de matrícula único (indexado para login).
        email: Email do oficial (único, opcional).
        senha_hash: Hash bcrypt da senha (gerada pelo admin, uso único).
        posto_graduacao: Posto ou graduação PM (ex: "Sargento"). Ver POSTOS_GRADUACAO.
        nome_guerra: Nome de guerra do agente (ex: "Silva"). Máx 50 chars.
        foto_url: URL pública da foto de perfil no R2 (opcional).
        session_id: UUID da sessão ativa. None = sem sessão. Novo login gera novo UUID.
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
    posto_graduacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nome_guerra: Mapped[str | None] = mapped_column(String(50), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    guarnicao_id: Mapped[int] = mapped_column(ForeignKey("guarnicoes.id"), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    guarnicao = relationship(
        "Guarnicao",
        back_populates="membros",
        foreign_keys=[guarnicao_id],
        lazy="selectin",
    )
