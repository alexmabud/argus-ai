"""Router agregador da API versão 1.

Centraliza todos os routers de domínio da versão 1 da API. Inclui
subrouters de autenticação, CRUD operacional (pessoas, veículos,
abordagens), upload de fotos, catálogo de passagens, relacionamentos
e consulta unificada.
"""

from fastapi import APIRouter

from app.api.v1.abordagens import router as abordagens_router
from app.api.v1.auth import router as auth_router
from app.api.v1.consultas import router as consultas_router
from app.api.v1.fotos import router as fotos_router
from app.api.v1.passagens import router as passagens_router
from app.api.v1.pessoas import router as pessoas_router
from app.api.v1.relacionamentos import router as relacionamentos_router
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

# Routers futuros (Fase 3+):
# api_router.include_router(ocorrencias.router)
# api_router.include_router(rag.router)
# api_router.include_router(legislacao.router)
# api_router.include_router(analytics.router)
# api_router.include_router(sync.router)
