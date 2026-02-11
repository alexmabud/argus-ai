from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router)

# Routers serão incluídos aqui conforme forem criados:
# api_router.include_router(pessoas.router)
# api_router.include_router(veiculos.router)
# api_router.include_router(abordagens.router)
# api_router.include_router(ocorrencias.router)
# api_router.include_router(fotos.router)
# api_router.include_router(consultas.router)
# api_router.include_router(relacionamentos.router)
# api_router.include_router(rag.router)
# api_router.include_router(legislacao.router)
# api_router.include_router(analytics.router)
# api_router.include_router(sync.router)
