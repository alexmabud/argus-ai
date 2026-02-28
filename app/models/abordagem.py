"""Modelo de Abordagem — registro principal de campo.

Define a abordagem em campo e suas tabelas de associação (pessoas,
veículos, fotos, passagens). Abordagem é o "documento" raiz do sistema.
"""

from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class Abordagem(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Registro de abordagem em campo.

    Documento raiz que materializa uma abordagem realizada por um oficial
    em uma data/hora e local específicos. Conecta pessoas, veículos,
    fotos, passagens e gera ocorrências.

    Attributes:
        id: Identificador único (chave primária).
        data_hora: Data/hora da abordagem (timezone-aware, indexada).
        latitude: Latitude GPS (opcional).
        longitude: Longitude GPS (opcional).
        localizacao: Ponto geográfico (PostGIS, SRID 4326).
        endereco_texto: Endereço em texto livre.
        observacao: Anotações do oficial.
        usuario_id: ID do oficial que realizou (FK).
        origem: Origem ("online", "offline" para sincronização).
        client_id: ID único do cliente que criou (offline-first).
        guarnicao_id: ID da guarnição (isolamento multi-tenant).
        pessoas: Relacionamento M:N com Pessoa via AbordagemPessoa.
        veiculos: Relacionamento M:N com Veiculo via AbordagemVeiculo.
        fotos: Relacionamento com Foto.
        passagens: Relacionamento M:N com Passagem via AbordagemPassagem.
        ocorrencias: Relacionamento com Ocorrencia.

    Nota:
        - Índice composto (guarnicao_id, data_hora) para filtros temporais.
        - GiST index em localizacao para queries geoespaciais.
        - client_id único apenas quando não-null (offline sync).
        - Cascata delete-orphan nas associações.
    """

    __tablename__ = "abordagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    localizacao = mapped_column(Geography("POINT", srid=4326), nullable=True)
    endereco_texto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    origem: Mapped[str] = mapped_column(String(20), default="online")
    client_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    pessoas = relationship(
        "AbordagemPessoa",
        back_populates="abordagem",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    veiculos = relationship(
        "AbordagemVeiculo",
        back_populates="abordagem",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    fotos = relationship("Foto", back_populates="abordagem", lazy="selectin")
    passagens = relationship(
        "AbordagemPassagem",
        back_populates="abordagem",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    ocorrencias = relationship("Ocorrencia", back_populates="abordagem", lazy="selectin")

    __table_args__ = (
        Index("idx_abordagem_guarnicao_data", "guarnicao_id", "data_hora"),
        Index("idx_abordagem_localizacao", "localizacao", postgresql_using="gist"),
        Index(
            "idx_abordagem_client_id",
            "client_id",
            unique=True,
            postgresql_where="client_id IS NOT NULL",
        ),
    )


class AbordagemPessoa(Base):
    """Associação M:N entre abordagem e pessoa.

    Tabela de junção que materializa a relação entre uma abordagem
    e as pessoas abordadas nela. Garante unicidade por índice.

    Attributes:
        id: Identificador único (chave primária).
        abordagem_id: ID da abordagem (FK, CASCADE delete).
        pessoa_id: ID da pessoa (FK, CASCADE delete).
        abordagem: Relacionamento com Abordagem.
        pessoa: Relacionamento com Pessoa.

    Nota:
        - Índice único (abordagem_id, pessoa_id) evita duplicatas.
    """

    __tablename__ = "abordagem_pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id", ondelete="CASCADE"))
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"))

    abordagem = relationship("Abordagem", back_populates="pessoas")
    pessoa = relationship("Pessoa", back_populates="abordagens")

    __table_args__ = (Index("uq_abordagem_pessoa", "abordagem_id", "pessoa_id", unique=True),)


class AbordagemVeiculo(Base):
    """Associação M:N entre abordagem e veículo.

    Tabela de junção que materializa a relação entre uma abordagem
    e os veículos envolvidos nela.

    Attributes:
        id: Identificador único (chave primária).
        abordagem_id: ID da abordagem (FK, CASCADE delete).
        veiculo_id: ID do veículo (FK, CASCADE delete).
        abordagem: Relacionamento com Abordagem.
        veiculo: Relacionamento com Veiculo.

    Nota:
        - Índice único (abordagem_id, veiculo_id) evita duplicatas.
    """

    __tablename__ = "abordagem_veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id", ondelete="CASCADE"))
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id", ondelete="CASCADE"))

    abordagem = relationship("Abordagem", back_populates="veiculos")
    veiculo = relationship("Veiculo")

    __table_args__ = (Index("uq_abordagem_veiculo", "abordagem_id", "veiculo_id", unique=True),)


class AbordagemPassagem(Base):
    """Associação entre abordagem, pessoa e passagem criminal.

    Tabela de junção que registra qual passagem (crime/infração)
    foi encontrada com qual pessoa em qual abordagem.

    Attributes:
        id: Identificador único (chave primária).
        abordagem_id: ID da abordagem (FK, CASCADE delete).
        pessoa_id: ID da pessoa envolvida (FK, CASCADE delete).
        passagem_id: ID da passagem/crime (FK, sem cascade).
        abordagem: Relacionamento com Abordagem.
        pessoa: Relacionamento com Pessoa.
        passagem: Relacionamento com Passagem.

    Nota:
        - Índice único triplo (abordagem_id, passagem_id, pessoa_id).
    """

    __tablename__ = "abordagem_passagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id", ondelete="CASCADE"))
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"))
    passagem_id: Mapped[int] = mapped_column(ForeignKey("passagens.id"))

    abordagem = relationship("Abordagem", back_populates="passagens")
    pessoa = relationship("Pessoa")
    passagem = relationship("Passagem")

    __table_args__ = (
        Index(
            "uq_abordagem_passagem",
            "abordagem_id",
            "passagem_id",
            "pessoa_id",
            unique=True,
        ),
    )
