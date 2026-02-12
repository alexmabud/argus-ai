"""Schemas Pydantic para consulta unificada cross-domain.

Define estruturas para busca simultânea em pessoas, veículos e abordagens
através de um único endpoint de consulta.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.abordagem import AbordagemRead
from app.schemas.pessoa import PessoaRead
from app.schemas.veiculo import VeiculoRead


class ConsultaUnificadaResponse(BaseModel):
    """Resposta da consulta unificada cross-domain.

    Retorna resultados combinados de busca em pessoas, veículos e abordagens.

    Attributes:
        pessoas: Lista de pessoas encontradas.
        veiculos: Lista de veículos encontrados.
        abordagens: Lista de abordagens encontradas.
        total_resultados: Total de resultados combinados.
    """

    pessoas: list[PessoaRead] = []
    veiculos: list[VeiculoRead] = []
    abordagens: list[AbordagemRead] = []
    total_resultados: int = 0
