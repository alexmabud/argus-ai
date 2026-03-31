"""Modelo de Localidade — hierarquia de estados, cidades e bairros.

Armazena localidades de forma hierárquica (estado → cidade → bairro)
para uso em endereços com autocomplete e sem duplicatas.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Localidade(Base, TimestampMixin):
    """Localidade geográfica hierárquica (estado, cidade ou bairro).

    Armazena estados, cidades e bairros em uma única tabela hierárquica
    com parent_id apontando para o nível acima. Estados não têm pai.
    A busca usa o campo `nome` normalizado (sem acento, minúsculas).

    Attributes:
        id: Identificador único.
        nome: Nome normalizado para busca (sem acento, minúsculas).
        nome_exibicao: Nome original para exibição ao usuário.
        tipo: Nível hierárquico — 'estado', 'cidade' ou 'bairro'.
        sigla: Sigla UF de 2 letras (apenas para estados).
        parent_id: FK para o nível acima (null para estados).
        ativo: Se a localidade está disponível para uso.
        parent: Relacionamento com localidade pai.
        filhos: Localidades filhas (cidades de um estado, bairros de uma cidade).
    """

    __tablename__ = "localidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    nome_exibicao: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(10))  # 'estado' | 'cidade' | 'bairro'
    sigla: Mapped[str | None] = mapped_column(String(2), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("localidades.id"), nullable=True, index=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    parent: Mapped[Localidade | None] = relationship(
        "Localidade", back_populates="filhos", remote_side="Localidade.id"
    )
    filhos: Mapped[list[Localidade]] = relationship("Localidade", back_populates="parent")
