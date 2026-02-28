"""Modelo de Pessoa — entidade central da memória operacional.

Define a pessoa abordada, com dados pessoais, endereços, fotos,
histórico de abordagens e relacionamentos com outras pessoas.
"""

from datetime import date

from sqlalchemy import Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class Pessoa(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Pessoa abordada — entidade central do sistema.

    Representa uma pessoa abordada pelo patrulhamento. Armazena dados pessoais,
    com CPF criptografado (Fernet) e hash SHA-256 para buscas.
    Conecta endereços, fotos, abordagens, ocorrências e relacionamentos.

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome completo (indexado, busca fuzzy via pg_trgm).
        cpf_encrypted: CPF criptografado com Fernet (nunca em plain text).
        cpf_hash: Hash SHA-256 do CPF para buscas (único para evitar duplicatas).
        data_nascimento: Data de nascimento (opcional).
        apelido: Apelido ou "nome de rua" (opcional).
        foto_principal_url: URL da foto de perfil (R2/S3).
        observacoes: Anotações sobre a pessoa.
        guarnicao_id: ID da guarnição (isolamento multi-tenant).
        enderecos: Relacionamento com EndereçosPessoa.
        abordagens: Relacionamento M:N com Abordagens via AbordagemPessoa.
        fotos: Relacionamento com Fotos.
        relacionamentos_como_a: Relacionamento bidirecional com outras pessoas (A->B).
        relacionamentos_como_b: Relacionamento bidirecional com outras pessoas (B->A).

    Nota:
        - Soft delete: ativo=True por padrão, desativado_em registra quando.
        - Busca fuzzy: índice GIN com gin_trgm_ops para matching aproximado.
        - CPF seguro: criptografia Fernet + hash para LGPD.
    """

    __tablename__ = "pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(300), index=True)
    cpf_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpf_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    apelido: Mapped[str | None] = mapped_column(String(100), nullable=True)
    foto_principal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    enderecos = relationship("EnderecoPessoa", back_populates="pessoa", lazy="selectin")
    abordagens = relationship("AbordagemPessoa", back_populates="pessoa", lazy="selectin")
    fotos = relationship("Foto", back_populates="pessoa", lazy="selectin")

    relacionamentos_como_a = relationship(
        "RelacionamentoPessoa",
        foreign_keys="RelacionamentoPessoa.pessoa_id_a",
        back_populates="pessoa_a",
        lazy="selectin",
    )
    relacionamentos_como_b = relationship(
        "RelacionamentoPessoa",
        foreign_keys="RelacionamentoPessoa.pessoa_id_b",
        back_populates="pessoa_b",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "idx_pessoa_nome_trgm",
            "nome",
            postgresql_using="gin",
            postgresql_ops={"nome": "gin_trgm_ops"},
        ),
        Index("idx_pessoa_guarnicao", "guarnicao_id"),
    )
