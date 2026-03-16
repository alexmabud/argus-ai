"""Router de autenticação e gerenciamento de usuários.

Fornece endpoints para login, refresh de tokens e obtenção
de dados do usuário autenticado. Implementa rate limiting para proteção
contra abuso.
"""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import (
    LoginRequest,
    PerfilUpdate,
    RefreshRequest,
    TokenResponse,
    UsuarioRead,
)
from app.services.auth_service import AuthService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/auth", tags=["Auth"])


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


@router.put("/perfil", response_model=UsuarioRead)
async def atualizar_perfil(
    data: PerfilUpdate,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioRead:
    """Atualiza nome, nome de guerra, posto/graduação e foto_url do perfil.

    Endpoint PUT — atualização completa do perfil. O campo nome é obrigatório.
    Os demais campos são opcionais (None = manter sem valor).

    Args:
        data: Dados de perfil a atualizar (nome obrigatório, demais opcionais).
        user: Usuário autenticado (injetado automaticamente).
        db: Sessão do banco de dados.

    Returns:
        UsuarioRead: Dados atualizados do usuário.

    Raises:
        AuthenticationError: Se token inválido ou sessão encerrada.
        ValidationError: Se posto_graduacao fora da lista oficial.

    Status Code:
        200: Perfil atualizado com sucesso.
        401: Não autenticado ou sessão inválida.
        422: Dados inválidos (posto fora da lista).
    """
    user.nome = data.nome
    if data.nome_guerra is not None:
        user.nome_guerra = data.nome_guerra
    if data.posto_graduacao is not None:
        user.posto_graduacao = data.posto_graduacao
    if data.foto_url is not None:
        user.foto_url = data.foto_url
    await db.commit()
    await db.refresh(user)
    return UsuarioRead.model_validate(user)


@router.post("/perfil/foto", response_model=dict)
async def upload_foto_perfil(
    foto: UploadFile = File(...),
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Faz upload da foto de perfil para R2 e atualiza foto_url do usuário.

    Args:
        foto: Arquivo de imagem enviado via multipart/form-data.
        user: Usuário autenticado.
        db: Sessão do banco de dados.

    Returns:
        dict: Objeto com campo foto_url contendo a URL pública da foto no R2.

    Raises:
        AuthenticationError: Se token inválido.

    Status Code:
        200: Upload realizado com sucesso.
        401: Não autenticado.
    """
    file_bytes = await foto.read()
    storage = StorageService()
    key = storage._generate_key("avatares", foto.filename or "foto.jpg")
    url = await storage.upload(file_bytes, key, content_type=foto.content_type or "image/jpeg")

    user.foto_url = url
    await db.commit()

    return {"foto_url": url}
