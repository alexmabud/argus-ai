"""Schemas Pydantic para CRUD de Veículo.

Define estruturas de requisição e resposta para criação, atualização,
leitura e busca de veículos registrados em abordagens.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import UpperStr


class VeiculoCreate(BaseModel):
    """Requisição de criação de veículo.

    Placa é normalizada para uppercase automaticamente.

    Attributes:
        placa: Placa veicular (normalizada para uppercase).
        modelo: Modelo do veículo (ex: "Fiesta", "Hilux").
        cor: Cor do veículo (ex: "Branco", "Preto").
        ano: Ano de fabricação.
        tipo: Tipo de veículo (ex: "Carro", "Moto", "Caminhão").
        observacoes: Anotações adicionais.
        client_id: ID único gerado no frontend offline, para deduplicação
            de sync (achado #18/2026-07-13). Opcional — None em criação
            online direta.
    """

    placa: str = Field(..., min_length=7, max_length=10)
    modelo: UpperStr = Field(None, max_length=100)
    cor: UpperStr = Field(None, max_length=50)
    ano: int | None = None
    tipo: UpperStr = Field(None, max_length=50)
    observacoes: UpperStr = Field(None, max_length=500)
    client_id: str | None = Field(None, max_length=100)

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        """Normaliza placa para uppercase e remove espaços/traços.

        Args:
            v: Valor da placa informado.

        Returns:
            Placa normalizada em uppercase sem espaços ou traços.
        """
        return v.upper().replace("-", "").replace(" ", "")


class VeiculoUpdate(BaseModel):
    """Requisição de atualização parcial de veículo.

    Placa não pode ser alterada (imutável após criação).
    Apenas os campos enviados serão atualizados.

    Attributes:
        modelo: Modelo atualizado.
        cor: Cor atualizada.
        ano: Ano atualizado.
        tipo: Tipo atualizado.
        observacoes: Anotações atualizadas.
    """

    modelo: UpperStr = Field(None, max_length=100)
    cor: UpperStr = Field(None, max_length=50)
    ano: int | None = None
    tipo: UpperStr = Field(None, max_length=50)
    observacoes: UpperStr = Field(None, max_length=500)


class VeiculoRead(BaseModel):
    """Dados públicos de um veículo (leitura).

    Attributes:
        id: Identificador único do veículo.
        placa: Placa veicular (normalizada uppercase).
        modelo: Modelo do veículo.
        cor: Cor do veículo.
        ano: Ano de fabricação.
        tipo: Tipo de veículo.
        observacoes: Anotações adicionais.
        guarnicao_id: ID da guarnição.
        criado_em: Timestamp de criação.
        atualizado_em: Timestamp de última atualização.
    """

    id: int
    placa: str
    modelo: str | None = None
    cor: str | None = None
    ano: int | None = None
    tipo: str | None = None
    observacoes: str | None = None
    guarnicao_id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}
