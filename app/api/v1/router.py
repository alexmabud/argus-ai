"""Router agregador da API versão 1.

Centraliza todos os routers de domínio da versão 1 da API. Inclui
subrouters de autenticação, CRUD operacional (pessoas, veículos,
abordagens), upload de fotos, catálogo de passagens, relacionamentos,
consulta unificada, ocorrências, legislação, RAG, analytics e sync.
"""

from fastapi import APIRouter

from app.api.v1.abordagens import router as abordagens_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.consultas import router as consultas_router
from app.api.v1.fotos import router as fotos_router
from app.api.v1.legislacao import router as legislacao_router
from app.api.v1.ocorrencias import router as ocorrencias_router
from app.api.v1.passagens import router as passagens_router
from app.api.v1.pessoas import router as pessoas_router
from app.api.v1.rag import router as rag_router
from app.api.v1.relacionamentos import router as relacionamentos_router
from app.api.v1.sync import router as sync_router
from app.api.v1.veiculos import router as veiculos_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(pessoas_router)
api_router.include_router(veiculos_router)
api_router.include_router(abordagens_router)
api_router.include_router(fotos_router)
api_router.include_router(passagens_router)
api_router.include_router(relacionamentos_router)
api_router.include_router(consultas_router)
api_router.include_router(ocorrencias_router)
api_router.include_router(legislacao_router)
api_router.include_router(rag_router)
api_router.include_router(analytics_router)
api_router.include_router(sync_router)
