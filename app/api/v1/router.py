"""Router agregador da API versão 1.

Centraliza todos os routers de domínio da versão 1 da API. Inclui
subrouters de autenticação, CRUD operacional (pessoas, veículos,
abordagens), upload de fotos, relacionamentos,
consulta unificada, ocorrências, analytics, sync e administração.
"""

from fastapi import APIRouter

from app.api.v1.abordagens import router as abordagens_router
from app.api.v1.admin import router as admin_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.consultas import router as consultas_router
from app.api.v1.fotos import router as fotos_router
from app.api.v1.localidades import router as localidades_router
from app.api.v1.ocorrencias import router as ocorrencias_router
from app.api.v1.pessoas import router as pessoas_router
from app.api.v1.sync import router as sync_router
from app.api.v1.veiculos import router as veiculos_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(pessoas_router)
api_router.include_router(veiculos_router)
api_router.include_router(abordagens_router)
api_router.include_router(fotos_router)
api_router.include_router(consultas_router)
api_router.include_router(ocorrencias_router)
api_router.include_router(analytics_router)
api_router.include_router(sync_router)
api_router.include_router(admin_router)
api_router.include_router(localidades_router)
