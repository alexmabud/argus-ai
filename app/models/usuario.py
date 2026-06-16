"""Modelo de Usuário — oficial ou membro da guarnição.

Define o usuário (oficial de patrulhamento) do sistema, com autenticação,
perfil (posto, nome de guerra, foto) e controle de sessão exclusiva.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
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
        foto_url: URL pública da foto de perfil no storage S3-compatible (opcional).
        session_id: UUID da sessão ativa. None = sem sessão. Novo login gera novo UUID.
        senha_expira_em: Timestamp de expiração da senha provisória. NULL = sem expiração.
            Senhas geradas pelo admin expiram em SENHA_PROVISORIA_EXPIRE_HOURS horas.
            Zerado no primeiro login bem-sucedido. Admin é isento de expiração.
        totp_secret: Secret TOTP cifrado com Fernet (AES-256). NULL = sem 2FA configurado.
            Apenas admins usam 2FA. Login de admin sem secret funciona normalmente
            (fase de bootstrap/enrollment). Enrollment via POST /admin/2fa/setup.
        guarnicao_id: ID da Equipe (guarnição) à qual o usuário pertence.
            FK para guarnicoes.id, nullable. Usuários sem equipe aparecem
            na aba "Sem Equipe" do painel admin e têm acesso restrito
            a abordagens (retorna 403 nos endpoints).
        is_admin: Flag indicando admin delegado (poderes granulares via flags pode_*).
        is_super_admin: Dono único do sistema. Faz tudo; é o único que promove/rebaixa
            admins e exclui usuários. Definido só por script (nunca pela UI).
        pode_criar_usuario: Admin delegado pode criar novos usuários.
        pode_gerar_senha: Admin delegado pode gerar nova senha de uso único.
        pode_pausar: Admin delegado pode pausar (desconectar) usuários.
        pode_mover_equipe: Admin delegado pode mover usuários entre equipes.
        pode_gerir_equipes: Admin delegado pode criar/editar equipes e BPMs
            (só efetivo quando admin_global=True, pois estrutura é global).
        admin_global: Alcance do admin delegado — True age sobre todas as equipes,
            False restringe à própria guarnição.
        guarnicao: Relacionamento com Guarnicao (= Equipe na UI).
        abordagens: Relacionamento com Abordagem (não carregado por padrão, lazy=noload).
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
    guarnicao_id: Mapped[int | None] = mapped_column(ForeignKey("guarnicoes.id"), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    pode_criar_usuario: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    pode_gerar_senha: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    pode_pausar: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    pode_mover_equipe: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    pode_gerir_equipes: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    admin_global: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    tentativas_falhas: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    senha_expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @property
    def totp_ativo(self) -> bool:
        """Indica se o 2FA TOTP está configurado para este usuário."""
        return self.totp_secret is not None

    guarnicao = relationship(
        "Guarnicao",
        back_populates="membros",
        foreign_keys=[guarnicao_id],
        lazy="selectin",
    )
    abordagens = relationship(
        "Abordagem",
        back_populates="usuario",
        lazy="noload",
        foreign_keys="[Abordagem.usuario_id]",
    )
