"""Schemas Pydantic para endpoints RAG (Retrieval-Augmented Generation).

Define estruturas de requisição e resposta para geração de relatórios
operacionais via LLM e busca semântica cross-domain em ocorrências
e legislação.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.legislacao import LegislacaoSemanticaRead
from app.schemas.ocorrencia import OcorrenciaDetail


class RelatorioRequest(BaseModel):
    """Requisição de geração de relatório operacional via RAG.

    Attributes:
        abordagem_id: ID da abordagem para gerar relatório.
        instrucao: Instrução adicional para o LLM (opcional,
            ex: "Foque nos aspectos de trânsito").
    """

    abordagem_id: int
    instrucao: str = Field(
        "",
        max_length=2000,
        description="Instrução adicional para o relatório",
    )


class RelatorioResponse(BaseModel):
    """Resposta de geração de relatório operacional via RAG.

    Attributes:
        relatorio: Texto do relatório gerado pelo LLM.
        fontes_ocorrencias: Ocorrências usadas como contexto.
        fontes_legislacao: Artigos de lei usados como referência.
        metricas: Métricas de qualidade do RAG.
    """

    relatorio: str
    fontes_ocorrencias: list[dict] = []
    fontes_legislacao: list[dict] = []
    metricas: dict = {}


class BuscaSemanticaRequest(BaseModel):
    """Requisição de busca semântica cross-domain.

    Attributes:
        query: Termo de busca em linguagem natural.
        top_k: Número máximo de resultados por tipo (1-20, padrão 5).
    """

    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)


class BuscaSemanticaResponse(BaseModel):
    """Resposta de busca semântica cross-domain.

    Attributes:
        ocorrencias: Ocorrências encontradas por similaridade.
        legislacoes: Artigos de lei encontrados por similaridade.
    """

    ocorrencias: list[OcorrenciaDetail] = []
    legislacoes: list[LegislacaoSemanticaRead] = []
