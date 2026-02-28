"""Modelo de Foto — imagens para reconhecimento facial e arquivo.

Define fotos de pessoas ou registros de abordagens com embeddings
faciais para busca por similaridade facial (InsightFace).
"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Foto(Base, TimestampMixin):
    """Foto de pessoa ou abordagem, com embedding facial opcional.

    Armazena fotos capturadas de pessoas ou durante abordagens.
    Cada foto pode ser processada para extrair embedding facial
    (512 dimensões via InsightFace) para busca por rosto.

    Attributes:
        id: Identificador único (chave primária).
        arquivo_url: URL da imagem em R2/S3 (Cloudflare).
        tipo: Tipo de foto (default: "rosto", ex: "corpo", "placa").
        data_hora: Data/hora da captura (timezone-aware).
        latitude: Latitude GPS (opcional).
        longitude: Longitude GPS (opcional).
        pessoa_id: ID da pessoa (FK, opcional - null para fotos de abordagem).
        abordagem_id: ID da abordagem (FK, opcional).
        embedding_face: Vetor facial 512-dimensional (pgvector).
        face_processada: Flag indicando se embedding foi extraído.
        pessoa: Relacionamento com Pessoa.
        abordagem: Relacionamento com Abordagem.

    Nota:
        - Embedding facial é processado via arq worker (async).
        - IVFFlat index no banco para busca por similaridade.
        - Uma foto pode estar associada a pessoa, abordagem ou ambas.
    """

    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    arquivo_url: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(50), default="rosto")
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    pessoa_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True)
    abordagem_id: Mapped[int | None] = mapped_column(ForeignKey("abordagens.id"), nullable=True)
    embedding_face = mapped_column(Vector(512), nullable=True)
    face_processada: Mapped[bool] = mapped_column(Boolean, default=False)

    pessoa = relationship("Pessoa", back_populates="fotos")
    abordagem = relationship("Abordagem", back_populates="fotos")
