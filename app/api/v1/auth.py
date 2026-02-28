"""Router de autenticação e gerenciamento de usuários.

Fornece endpoints para registro, login, refresh de tokens e obtenção
de dados do usuário autenticado. Implementa rate limiting para proteção
contra abuso.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UsuarioRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UsuarioRead:
    """Registra um novo agente na guarnição.

    Cria novo usuário com senha hasheada e realiza validações de duplicação
    de matrícula e email. Registra evento de auditoria.

    Args:
        request: Objeto Request do FastAPI (para capturar IP e User-Agent).
        data: Dados de registro (nome, matrícula, senha, email, guarnicao_id).
        db: Sessão do banco de dados (injetada automaticamente).

    Returns:
        UsuarioRead: Dados do usuário criado (sem senha).

    Raises:
        ConflitoDadosError: Se matrícula ou email já estão cadastrados.
        ValidationError: Se dados de entrada são inválidos.

    Status Code:
        201: Usuário criado com sucesso.
        400: Dados inválidos ou matrícula/email duplicados.
        429: Muitas requisições no período (rate limit: 5/minuto).
    """
    service = AuthService(db)
    usuario = await service.register(
        data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UsuarioRead.model_validate(usuario)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Autentica um agente e retorna tokens de acesso.

    Valida as credenciais (matrícula e senha) e gera tokens JWT de acesso
    (curta duração) e refresh (longa duração). Registra evento de login
    na auditoria.

    Args:
        request: Objeto Request do FastAPI (para capturar IP e User-Agent).
        data: Credenciais de login (matrícula e senha).
        db: Sessão do banco de dados (injetada automaticamente).

    Returns:
        TokenResponse: Tokens JWT de acesso e refresh.

    Raises:
        CredenciaisInvalidasError: Se matrícula não existe ou senha é inválida.
        ValidationError: Se dados de entrada são inválidos.

    Status Code:
        200: Autenticação realizada com sucesso.
        400: Dados inválidos ou credenciais inválidas.
        429: Muitas requisições no período (rate limit: 10/minuto).

    Note:
        O access_token deve ser incluído no header Authorization (Bearer)
        para requisições subsequentes.
    """
    service = AuthService(db)
    return await service.login(
        data.matricula,
        data.senha,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Renova o token de acesso usando um refresh token.

    Valida o refresh token e gera novos tokens de acesso e refresh.
    Útil para manter a sessão ativa sem exigir re-autenticação.

    Args:
        request: Objeto Request do FastAPI.
        data: Requisição contendo o refresh token válido.
        db: Sessão do banco de dados (injetada automaticamente).

    Returns:
        TokenResponse: Novos tokens JWT de acesso e refresh.

    Raises:
        CredenciaisInvalidasError: Se o refresh token é inválido ou o
            usuário não existe ou está inativo.
        ValidationError: Se dados de entrada são inválidos.

    Status Code:
        200: Tokens renovados com sucesso.
        400: Refresh token inválido ou usuário não existe.
        429: Muitas requisições no período (rate limit: 30/minuto).
    """
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.get("/me", response_model=UsuarioRead)
async def me(user: Usuario = Depends(get_current_user)) -> UsuarioRead:
    """Retorna dados do usuário autenticado.

    Endpoint protegido que retorna as informações do usuário atualmente
    autenticado, extraído do token JWT no header Authorization.

    Args:
        user: Usuário autenticado (injetado automaticamente via dependency).

    Returns:
        UsuarioRead: Dados públicos do usuário autenticado.

    Raises:
        AuthenticationError: Se o token é inválido, expirado ou ausente.

    Status Code:
        200: Sucesso com dados do usuário.
        401: Token não fornecido ou inválido.

    Security:
        Requer autenticação via Bearer token no header Authorization.
    """
    return UsuarioRead.model_validate(user)
