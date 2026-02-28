"""Modelo de Veículo — registro de veículos abordados.

Define veículos registrados durante abordagens, com dados
de identificação e cadastro.
"""

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class Veiculo(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Veículo registrado em abordagem.

    Armazena informações de veículos abordados durante operações.
    Cada veículo é identificado unicamente por placa e isolado
    por guarnição (multi-tenant).

    Attributes:
        id: Identificador único (chave primária).
        placa: Placa veicular (único, indexado para buscas).
        modelo: Modelo do veículo (ex: "Fiesta", "Hilux").
        cor: Cor do veículo (ex: "Branco", "Preto").
        ano: Ano de fabricação.
        tipo: Tipo de veículo (ex: "Carro", "Moto", "Caminhão").
        observacoes: Anotações adicionais.
        guarnicao_id: ID da guarnição (isolamento multi-tenant).

    Nota:
        - Placa é única globalmente e indexada.
        - Soft delete: dados nunca são removidos.
    """

    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ano: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (Index("idx_veiculo_guarnicao", "guarnicao_id"),)
