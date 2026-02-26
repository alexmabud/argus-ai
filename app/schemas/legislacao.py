"""Schemas Pydantic para CRUD de Legislação.

Define estruturas de requisição e resposta para criação, leitura
e busca semântica de artigos de lei e legislação criminal.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LegislacaoCreate(BaseModel):
    """Requisição de criação de artigo de legislação.

    Attributes:
        lei: Lei ou código (ex: "CP", "LCP", "Lei 11343/06").
        artigo: Número do artigo (ex: "121", "33").
        nome: Nome resumido do tipo penal (ex: "Homicídio Simples").
        texto: Texto integral do artigo de lei.
    """

    lei: str = Field(..., min_length=1, max_length=100)
    artigo: str = Field(..., min_length=1, max_length=50)
    nome: str | None = Field(None, max_length=300)
    texto: str = Field(..., min_length=1)


class LegislacaoRead(BaseModel):
    """Dados de leitura de um artigo de legislação.

    Attributes:
        id: Identificador único.
        lei: Lei ou código penal.
        artigo: Número do artigo.
        nome: Nome resumido do tipo penal.
        texto: Texto integral do artigo.
        ativo: Se o artigo está vigente.
        criado_em: Timestamp de criação.
        atualizado_em: Timestamp de última atualização.
    """

    id: int
    lei: str
    artigo: str
    nome: str | None = None
    texto: str
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class LegislacaoSemanticaRead(LegislacaoRead):
    """Dados de legislação com score de similaridade semântica.

    Estende LegislacaoRead com o score de similaridade cosseno
    retornado pela busca vetorial no pgvector.

    Attributes:
        similaridade: Score de similaridade cosseno (0-1).
    """

    similaridade: float = 0.0
