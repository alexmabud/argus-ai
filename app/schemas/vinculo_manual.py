"""Schemas Pydantic para vínculos manuais entre pessoas.

Define estruturas de requisição e resposta para criação e leitura
de vínculos manuais cadastrados pelo operador.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VinculoManualCreate(BaseModel):
    """Requisição de criação de vínculo manual.

    Attributes:
        pessoa_vinculada_id: ID da pessoa a ser vinculada.
        tipo: Tipo do vínculo (ex: 'Irmão', 'Pai', 'Sócio'). Obrigatório.
        descricao: Detalhe adicional sobre o vínculo (opcional).
    """

    pessoa_vinculada_id: int
    tipo: str = Field(..., min_length=1, max_length=100)
    descricao: str | None = Field(None, max_length=500)


class VinculoManualRead(BaseModel):
    """Dados de leitura de vínculo manual.

    Attributes:
        id: Identificador único do vínculo.
        pessoa_vinculada_id: ID da pessoa vinculada.
        nome: Nome da pessoa vinculada.
        foto_principal_url: URL da foto da pessoa vinculada (para exibição).
        tipo: Tipo do vínculo (ex: 'Irmão').
        descricao: Detalhe adicional sobre o vínculo.
        criado_em: Timestamp de criação do vínculo.
    """

    id: int
    pessoa_vinculada_id: int
    nome: str
    foto_principal_url: str | None = None
    tipo: str
    descricao: str | None = None
    criado_em: datetime

    model_config = {"from_attributes": True}
