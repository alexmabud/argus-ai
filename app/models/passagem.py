"""Modelo de Passagem — tipo penal ou infração administrativa.

Define os tipos de passagens criminais e infrações administrativas
registráveis durante abordagens.
"""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Passagem(Base, TimestampMixin):
    """Tipo penal ou infração administrativa.

    Catalogo de passagens criminais (tipos penais) e infrações administrativas
    que podem ser registradas durante abordagens. Cada passagem é identificada
    por lei e artigo (único).

    Attributes:
        id: Identificador único (chave primária).
        lei: Lei ou código penal (ex: "CP", "LCP", "Lei 11343/06").
        artigo: Número do artigo (ex: "121", "129", "33").
        nome_crime: Descrição do crime/infração (ex: "Homicídio Simples").

    Nota:
        Combinação (lei, artigo) é única, evitando duplicatas.
    """

    __tablename__ = "passagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    lei: Mapped[str] = mapped_column(String(100), index=True)
    artigo: Mapped[str] = mapped_column(String(50))
    nome_crime: Mapped[str] = mapped_column(String(300))

    __table_args__ = (Index("uq_passagem_lei_artigo", "lei", "artigo", unique=True),)
