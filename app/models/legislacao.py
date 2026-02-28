"""Modelo de Legislação — textos legais indexados para RAG.

Define legislação e textos legais que podem ser recuperados via
busca semântica através de embeddings vetoriais (pgvector).
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Legislacao(Base, TimestampMixin):
    """Legislação indexada para busca semântica via RAG.

    Armazena textos de legislação, constituição, decretos e portarias
    com embeddings vetoriais (384 dimensões) para recuperação semântica.
    Permite sistema de Retrieval-Augmented Generation (RAG) responder
    questões sobre legislação vigente.

    Attributes:
        id: Identificador único (chave primária).
        lei: Designação da lei (ex: "CF", "CP", "Lei 11343/06").
        artigo: Número do artigo.
        nome: Descrição do tópico legislativo (opcional).
        texto: Texto completo do artigo ou dispositivo.
        ativo: Flag indicando se legislação está vigente.
        embedding: Vetor semântico 384-dimensional (pgvector) para busca.

    Nota:
        - Combinação (lei, artigo) é única.
        - Embedding é gerado via SentenceTransformers offline/batch.
        - IVFFlat index no banco para busca vetorial eficiente.
    """

    __tablename__ = "legislacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lei: Mapped[str] = mapped_column(String(100), index=True)
    artigo: Mapped[str] = mapped_column(String(50))
    nome: Mapped[str | None] = mapped_column(String(300), nullable=True)
    texto: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding = mapped_column(Vector(384), nullable=True)

    __table_args__ = (Index("uq_legislacao_lei_artigo", "lei", "artigo", unique=True),)
