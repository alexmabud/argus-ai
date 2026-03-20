"""Dependências para injeção de dependências (DI) em FastAPI.

Fornece functions para extrair usuário autenticado via JWT bearer token,
além de acesso a serviços de IA (face recognition, embeddings) armazenados
no application state. Lazy loading de serviços pesados usa asyncio.Lock
para evitar race conditions em requisições concorrentes.
"""

import asyncio
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decodificar_token
from app.database.session import get_db
from app.models.usuario import Usuario

logger = logging.getLogger("argus")

#: Esquema de segurança HTTP Bearer para extrair token do header Authorization.
security = HTTPBearer()

#: Locks para evitar race condition no lazy load de serviços pesados.
_face_service_lock = asyncio.Lock()
_embedding_service_lock = asyncio.Lock()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Extrai e valida usuário autenticado do token JWT Bearer.

    Além de validar assinatura e expiração do JWT, verifica o session_id:
    o claim 'sid' do token deve corresponder ao session_id no banco.
    Isso garante sessão exclusiva — novo login invalida tokens anteriores.
    Usuários com session_id=None (pausados ou sem login) são sempre rejeitados.

    Args:
        credentials: Credencial Bearer extraída do header Authorization.
        db: Sessão do banco de dados para buscar usuário.

    Returns:
        Objeto Usuario autenticado, ativo e com sessão válida.

    Raises:
        HTTPException: 401 se token inválido, expirado, usuário inativo
            ou session_id não confere.
    """
    payload = decodificar_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido (sem sub)",
        )

    result = await db.execute(
        select(Usuario).where(Usuario.id == int(user_id), Usuario.ativo == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )

    # Verificar session_id — sessão exclusiva por usuário
    token_sid = payload.get("sid")
    if user.session_id is None or user.session_id != token_sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada — solicite nova senha ao administrador",
        )

    return user


async def get_face_service(request: Request):
    """Obtém serviço de reconhecimento facial do application state.

    Usa double-checked locking com asyncio.Lock para evitar race condition
    em requisições concorrentes que tentam inicializar o serviço ao mesmo
    tempo. Retorna None se InsightFace não estiver disponível.

    Args:
        request: Objeto Request do FastAPI.

    Returns:
        Instância de FaceService com InsightFace buffalo_l (512-dim),
        ou None se o serviço não estiver disponível.
    """
    face_service = request.app.state.face_service
    if face_service is not None:
        return face_service

    async with _face_service_lock:
        # Double-check: outra request pode ter inicializado enquanto esperávamos
        face_service = request.app.state.face_service
        if face_service is not None:
            return face_service
        try:
            from app.services.face_service import FaceService

            face_service = FaceService()
            request.app.state.face_service = face_service
        except Exception as exc:
            logger.warning("Serviço de reconhecimento facial indisponível: %s", exc)
            return None
    return face_service


async def get_embedding_service(request: Request):
    """Obtém serviço de embeddings do application state.

    Usa double-checked locking com asyncio.Lock para evitar inicialização
    duplicada em requisições concorrentes.

    Args:
        request: Objeto Request do FastAPI.

    Returns:
        Instância de EmbeddingService com SentenceTransformers (384-dim).
    """
    embedding_service = request.app.state.embedding_service
    if embedding_service is not None:
        return embedding_service

    async with _embedding_service_lock:
        embedding_service = request.app.state.embedding_service
        if embedding_service is not None:
            return embedding_service
        try:
            from app.services.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            request.app.state.embedding_service = embedding_service
        except Exception:
            logger.exception("Falha ao inicializar serviço de embeddings")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de embeddings indisponível",
            )
    return embedding_service
