"""Router RAG (Retrieval-Augmented Generation).

Fornece endpoints para geração de relatórios operacionais via LLM
com contexto semântico e busca cross-domain em ocorrências e legislação.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_embedding_service
from app.models.usuario import Usuario
from app.schemas.legislacao import LegislacaoSemanticaRead
from app.schemas.ocorrencia import OcorrenciaDetail
from app.schemas.rag import (
    BuscaSemanticaRequest,
    BuscaSemanticaResponse,
    RelatorioRequest,
    RelatorioResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/relatorio", response_model=RelatorioResponse)
@limiter.limit("10/minute")
async def gerar_relatorio(
    request: Request,
    data: RelatorioRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> RelatorioResponse:
    """Gera relatório operacional via pipeline RAG.

    Pipeline: recupera ocorrências e legislação semanticamente
    relevantes → monta contexto → gera relatório via LLM.
    Nunca inventa fatos — apenas organiza dados existentes.

    Args:
        request: Objeto Request do FastAPI.
        data: abordagem_id e instrução opcional.
        db: Sessão do banco de dados.
        user: Usuário autenticado.
        embedding_service: Serviço de embedding injetado.

    Returns:
        RelatorioResponse com texto, fontes e métricas.

    Status Code:
        429: Rate limit (10/min).
        503: LLM indisponível.
    """
    rag = RAGService(db, embedding_service)
    resultado = await rag.gerar_relatorio(
        abordagem_id=data.abordagem_id,
        instrucao=data.instrucao,
        guarnicao_id=user.guarnicao_id,
        usuario_id=user.id,
    )
    return RelatorioResponse(**resultado)


@router.post("/busca", response_model=BuscaSemanticaResponse)
@limiter.limit("30/minute")
async def buscar_semantica(
    request: Request,
    data: BuscaSemanticaRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> BuscaSemanticaResponse:
    """Busca semântica cross-domain (ocorrências + legislação).

    Gera embedding da query e busca simultaneamente em ocorrências
    (com filtro multi-tenant) e legislação (dados globais).

    Args:
        request: Objeto Request do FastAPI.
        data: Termo de busca e top_k.
        db: Sessão do banco de dados.
        user: Usuário autenticado.
        embedding_service: Serviço de embedding injetado.

    Returns:
        BuscaSemanticaResponse com ocorrências e legislações.

    Status Code:
        429: Rate limit (30/min).
    """
    rag = RAGService(db, embedding_service)

    ocorrencias_ctx = await rag.buscar_contexto(data.query, user.guarnicao_id, top_k=data.top_k)
    legislacao_ctx = await rag.buscar_legislacao(data.query, top_k=data.top_k)

    ocorrencias = [
        OcorrenciaDetail(
            id=item["ocorrencia"].id,
            numero_ocorrencia=item["ocorrencia"].numero_ocorrencia,
            abordagem_id=item["ocorrencia"].abordagem_id,
            arquivo_pdf_url=item["ocorrencia"].arquivo_pdf_url,
            processada=item["ocorrencia"].processada,
            usuario_id=item["ocorrencia"].usuario_id,
            guarnicao_id=item["ocorrencia"].guarnicao_id,
            texto_extraido=item["ocorrencia"].texto_extraido,
            similaridade=item["similaridade"],
            criado_em=item["ocorrencia"].criado_em,
            atualizado_em=item["ocorrencia"].atualizado_em,
        )
        for item in ocorrencias_ctx
    ]

    legislacoes = [
        LegislacaoSemanticaRead(
            id=item["legislacao"].id,
            lei=item["legislacao"].lei,
            artigo=item["legislacao"].artigo,
            nome=item["legislacao"].nome,
            texto=item["legislacao"].texto,
            ativo=item["legislacao"].ativo,
            criado_em=item["legislacao"].criado_em,
            atualizado_em=item["legislacao"].atualizado_em,
            similaridade=item["similaridade"],
        )
        for item in legislacao_ctx
    ]

    return BuscaSemanticaResponse(
        ocorrencias=ocorrencias,
        legislacoes=legislacoes,
    )
