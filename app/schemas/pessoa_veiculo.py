"""Schemas Pydantic para vínculo direto pessoa-veículo."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PessoaVeiculoRead(BaseModel):
    """Veículo de uma pessoa na listagem unificada da ficha.

    Attributes:
        veiculo_id: ID do veículo.
        placa: Placa veicular.
        modelo: Modelo do veículo.
        cor: Cor do veículo.
        ano: Ano de fabricação.
        tipo: Tipo de veículo.
        observacoes: Anotações adicionais.
        criado_em: Timestamp de cadastro do veículo (não do vínculo).
        origem: "direto" (vinculado pela ficha) ou "abordagem" (vinculado
            via alguma abordagem da pessoa). Só "direto" habilita o botão
            de desvincular no frontend.
    """

    veiculo_id: int
    placa: str
    modelo: str | None = None
    cor: str | None = None
    ano: int | None = None
    tipo: str | None = None
    observacoes: str | None = None
    criado_em: datetime
    origem: Literal["direto", "abordagem"]

    model_config = {"from_attributes": True}
