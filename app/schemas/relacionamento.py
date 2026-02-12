"""Schemas Pydantic para leitura de relacionamentos entre pessoas.

Define estruturas de resposta para consulta de vínculos
materializados entre pessoas abordadas juntas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.pessoa import PessoaRead


class RelacionamentoRead(BaseModel):
    """Dados completos de um relacionamento entre duas pessoas.

    Attributes:
        id: Identificador único do relacionamento.
        pessoa_a: Dados da pessoa A.
        pessoa_b: Dados da pessoa B.
        frequencia: Número de vezes abordadas juntas.
        primeira_vez: Timestamp da primeira abordagem conjunta.
        ultima_vez: Timestamp da última abordagem conjunta.
    """

    id: int
    pessoa_a: PessoaRead
    pessoa_b: PessoaRead
    frequencia: int
    primeira_vez: datetime
    ultima_vez: datetime

    model_config = {"from_attributes": True}
