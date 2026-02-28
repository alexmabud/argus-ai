"""Modelo de Endereço — endereços associados a pessoa.

Define endereços conhecidos de uma pessoa com localização geoespacial
(PostGIS) para análise de padrões de movimento.
"""

from datetime import date

from geoalchemy2 import Geography
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class EnderecoPessoa(Base, TimestampMixin, SoftDeleteMixin):
    """Endereço associado a uma pessoa.

    Armazena endereços conhecidos de uma pessoa (residência, local de trabalho,
    familiares, etc.) com localização geográfica para análise geoespacial
    (busca por raio, mapas de calor, padrões de movimento).

    Attributes:
        id: Identificador único (chave primária).
        pessoa_id: ID da pessoa (FK, CASCADE delete).
        endereco: Endereço em texto livre (até 500 chars).
        localizacao: Ponto geográfico POINT(lat, lon) em WGS84 (SRID 4326).
        data_inicio: Data do início da associação (opcional).
        data_fim: Data do fim da associação (opcional).
        pessoa: Relacionamento com Pessoa.

    Nota:
        - PostGIS POINT: permite queries geoespaciais (ST_DWithin, ST_Distance).
        - GiST index automático em localizacao para performance.
        - Datas permitem histórico temporal de endereços.
    """

    __tablename__ = "enderecos_pessoa"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"))
    endereco: Mapped[str] = mapped_column(String(500))
    localizacao = mapped_column(Geography("POINT", srid=4326), nullable=True)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)

    pessoa = relationship("Pessoa", back_populates="enderecos")
