"""Modelo de Ocorrência — documento policial formal.

Define a ocorrência policial formal gerada a partir de uma abordagem,
com PDF, texto extraído e embedding para busca semântica.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class Ocorrencia(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Ocorrência policial gerada a partir de abordagem.

    Representa o documento policial formal (BO - Boletim de Ocorrência)
    gerado a partir de uma abordagem. Inclui PDF, texto extraído via OCR
    e embedding para busca semântica.

    Attributes:
        id: Identificador único (chave primária).
        numero_ocorrencia: Número único do BO (ex: "2024.00001/GU01").
        abordagem_id: ID da abordagem origem (FK).
        arquivo_pdf_url: URL do PDF em R2/S3.
        texto_extraido: Texto extraído do PDF via EasyOCR (opcional).
        embedding: Vetor semântico 384-dimensional para busca.
        processada: Flag indicando se PDF foi processado (OCR + embedding).
        usuario_id: ID do oficial que gerou (FK).
        guarnicao_id: ID da guarnição (isolamento multi-tenant).
        abordagem: Relacionamento com Abordagem.

    Nota:
        - numero_ocorrencia é único globalmente.
        - Processamento async: OCR e embedding via arq worker.
        - IVFFlat index para busca vetorial.
    """

    __tablename__ = "ocorrencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_ocorrencia: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    arquivo_pdf_url: Mapped[str] = mapped_column(String(500))
    texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
    processada: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))

    abordagem = relationship("Abordagem", back_populates="ocorrencias")
