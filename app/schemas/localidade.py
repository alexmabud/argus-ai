"""Schemas Pydantic para criação e leitura de Localidade.

Define estruturas de requisição e resposta para o endpoint
de autocomplete e criação de localidades (estado, cidade, bairro).
"""

from pydantic import BaseModel, Field


class LocalidadeCreate(BaseModel):
    """Requisição de criação de nova localidade.

    Attributes:
        nome: Nome da localidade como digitado pelo usuário.
        tipo: Nível hierárquico — 'cidade' ou 'bairro' (estado não é criado via API).
        parent_id: ID da localidade pai (estado para cidade, cidade para bairro).
    """

    nome: str = Field(..., min_length=2, max_length=200)
    tipo: str = Field(..., pattern="^(cidade|bairro)$")
    parent_id: int


class LocalidadeRead(BaseModel):
    """Dados de leitura de uma localidade.

    Attributes:
        id: Identificador único.
        nome_exibicao: Nome original para exibição.
        tipo: Nível hierárquico.
        sigla: Sigla UF (apenas para estados).
        parent_id: ID da localidade pai.
    """

    id: int
    nome_exibicao: str
    tipo: str
    sigla: str | None = None
    parent_id: int | None = None

    model_config = {"from_attributes": True}
