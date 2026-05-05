"""Schemas Pydantic para BPM (Batalhão de Polícia Militar).

Define estruturas de requisição e resposta para listagem e criação de BPMs.
"""

from pydantic import BaseModel, Field


class BpmRead(BaseModel):
    """Dados de leitura de um BPM.

    Attributes:
        id: Identificador único do BPM.
        nome: Nome do batalhão (ex: "14º BPM").
        isolamento_abordagens: Se True, usuários do BPM veem apenas abordagens
            do próprio BPM.
    """

    id: int
    nome: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}


class BpmCreate(BaseModel):
    """Dados para criação de novo BPM.

    Attributes:
        nome: Nome do batalhão (1-200 caracteres).
    """

    nome: str = Field(..., min_length=1, max_length=200)


class BpmIsolamentoUpdate(BaseModel):
    """Dados para alternar isolamento de abordagens de um BPM.

    Attributes:
        isolamento_abordagens: True ativa isolamento por BPM, False desativa.
    """

    isolamento_abordagens: bool
