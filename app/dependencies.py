"""Dependências para injeção de dependências (DI) em FastAPI.

Fornece functions para extrair usuário autenticado via JWT bearer token,
além de acesso a serviços de IA (face recognition, embeddings) armazenados
no application state.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decodificar_token
from app.database.session import get_db
from app.models.usuario import Usuario

#: Esquema de segurança HTTP Bearer para extrair token do header Authorization.
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Extrai e valida usuário autenticado do token JWT Bearer.

    Decodifica token JWT, valida assinatura e expiration, busca usuário
    no banco de dados, e verifica se está ativo. Levanta exceção 401 se
    token inválido, expirado ou usuário não existe/inativo.

    Args:
        credentials: Credencial Bearer extraída do header Authorization.
        db: Sessão do banco de dados para buscar usuário.

    Returns:
        Objeto Usuario autenticado e ativo.

    Raises:
        HTTPException: 401 se token inválido, expirado ou usuário não existe.
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user


def get_face_service(request: Request):
    """Obtém serviço de reconhecimento facial do application state.

    Args:
        request: Objeto Request do FastAPI.

    Returns:
        Instância de FaceService com InsightFace buffalo_l (512-dim).
    """

    return request.app.state.face_service


def get_embedding_service(request: Request):
    """Obtém serviço de embeddings do application state.

    Args:
        request: Objeto Request do FastAPI.

    Returns:
        Instância de EmbeddingService com SentenceTransformers (384-dim).
    """

    return request.app.state.embedding_service
