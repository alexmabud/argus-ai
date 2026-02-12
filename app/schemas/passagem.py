"""Schemas Pydantic para CRUD de Passagem (tipo penal/infração).

Define estruturas de requisição e resposta para criação, leitura
e busca de passagens criminais e infrações administrativas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PassagemCreate(BaseModel):
    """Requisição de criação de passagem criminal.

    Attributes:
        lei: Lei ou código penal (ex: "CP", "LCP", "Lei 11343/06").
        artigo: Número do artigo (ex: "121", "129", "33").
        nome_crime: Descrição do crime/infração (ex: "Homicídio Simples").
    """

    lei: str = Field(..., min_length=1, max_length=100)
    artigo: str = Field(..., min_length=1, max_length=50)
    nome_crime: str = Field(..., min_length=1, max_length=300)


class PassagemRead(BaseModel):
    """Dados de leitura de uma passagem criminal.

    Attributes:
        id: Identificador único da passagem.
        lei: Lei ou código penal.
        artigo: Número do artigo.
        nome_crime: Descrição do crime/infração.
    """

    id: int
    lei: str
    artigo: str
    nome_crime: str

    model_config = {"from_attributes": True}


class PassagemVinculoRead(BaseModel):
    """Vínculo entre passagem e pessoa em uma abordagem.

    Attributes:
        passagem: Dados da passagem criminal.
        pessoa_id: ID da pessoa vinculada à passagem.
    """

    passagem: PassagemRead
    pessoa_id: int
