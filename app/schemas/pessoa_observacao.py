"""Schemas Pydantic para observações de pessoas.

Define estruturas de requisição e resposta para criação, atualização
e leitura de observações vinculadas a pessoas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PessoaObservacaoCreate(BaseModel):
    """Requisição de criação de observação.

    Attributes:
        texto: Conteúdo da observação. Obrigatório, mínimo 1 caractere.
    """

    texto: str = Field(..., min_length=1, max_length=2000)


class PessoaObservacaoUpdate(BaseModel):
    """Requisição de atualização de observação.

    Attributes:
        texto: Novo conteúdo da observação. Obrigatório, mínimo 1 caractere.
    """

    texto: str = Field(..., min_length=1, max_length=2000)


class PessoaObservacaoRead(BaseModel):
    """Dados de leitura de observação.

    Attributes:
        id: Identificador único.
        texto: Conteúdo da observação.
        criado_em: Timestamp de criação (para exibição na ficha).
    """

    id: int
    texto: str
    criado_em: datetime

    model_config = {"from_attributes": True}
