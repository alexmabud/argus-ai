"""Schemas Pydantic para BPM (Batalhão de Polícia Militar).

Define estruturas de requisição e resposta para listagem e criação de BPMs.
"""

from pydantic import BaseModel, Field


class BpmRead(BaseModel):
    """Dados de leitura de um BPM.

    Attributes:
        id: Identificador único do BPM.
        nome: Nome do batalhão (ex: "14º BPM").
    """

    id: int
    nome: str

    model_config = {"from_attributes": True}


class BpmCreate(BaseModel):
    """Dados para criação de novo BPM.

    Attributes:
        nome: Nome do batalhão (1-200 caracteres).
    """

    nome: str = Field(..., min_length=1, max_length=200)
