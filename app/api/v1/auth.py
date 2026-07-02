"""Router de autenticação e gerenciamento de usuários.

Fornece endpoints para login, refresh de tokens e obtenção
de dados do usuário autenticado. Implementa rate limiting para proteção
contra abuso.
"""

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookie import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    clear_access_cookie,
    clear_refresh_cookie,
    set_access_cookie,
    set_refresh_cookie,
)
from app.core.exceptions import ContaBloqueadaError, CredenciaisInvalidasError
from app.core.login_guard import ip_bloqueado, registrar_falha_ip, resetar_ip
from app.core.rate_limit import _get_real_client_ip, limiter
from app.core.upload_validation import ler_upload_com_limite, validar_magic_bytes_imagem
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
from app.services import notification_service
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
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
    ip = _get_real_client_ip(request)
    user_agent = request.headers.get("user-agent")

    if await ip_bloqueado(ip):
        await notification_service.alerta_ip_bloqueado(ip)
        raise ContaBloqueadaError("IP temporariamente bloqueado por excesso de tentativas")

    service = AuthService(db)
    try:
        tokens = await service.login(
            data.matricula,
            data.senha,
            ip_address=ip,
            user_agent=user_agent,
            totp_code=data.totp_code,
        )
    except CredenciaisInvalidasError:
        await AuditService(db).log(
            usuario_id=None,
            acao="LOGIN_FAILED",
            recurso="auth",
            detalhes={"matricula": data.matricula},
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.commit()
        await registrar_falha_ip(ip)
        raise
    await resetar_ip(ip)
    # Cookies HTTPOnly: access (path=/) e refresh (path restrito ao /refresh).
    set_access_cookie(response, tokens.access_token)
    set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
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
    # Preferir cookie (HttpOnly) ao corpo — fallback para compatibilidade
    token = request.cookies.get(REFRESH_TOKEN_COOKIE) or data.refresh_token
    if not token:
        raise CredenciaisInvalidasError()
    service = AuthService(db)
    tokens = await service.refresh(token)
    # Persiste a rotação de session_id feita no refresh (usuário comum).
    await db.commit()
    set_access_cookie(response, tokens.access_token)
    set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=204)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    response: Response,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Encerra a sessão revogando o session_id no servidor.

    Limpa o session_id do usuario no banco para que refresh tokens
    com o sid antigo falhem imediatamente. Antes desta task o logout
    apenas limpava o cookie, deixando o refresh token valido por 30 dias.

    Exige autenticacao (header Authorization Bearer ou cookie). Tokens
    expirados resultam em 401 — frontend deve descartar tokens locais
    mesmo nessa resposta.

    Args:
        request: Objeto Request do FastAPI.
        response: Resposta usada para emitir o Set-Cookie de remoção.
        user: Usuario autenticado.
        db: Sessao do banco para persistir a revogacao.

    Status Code:
        204: Sessão encerrada.
        401: Token ausente, invalido ou expirado.
    """
    user.session_id = None
    await db.commit()
    clear_access_cookie(response)
    clear_refresh_cookie(response)


@router.get("/me", response_model=UsuarioRead)
@limiter.limit("30/minute")
async def me(
    request: Request,
    response: Response,
    user: Usuario = Depends(get_current_user),
) -> UsuarioRead:
    """Retorna dados do usuário autenticado.

    Endpoint protegido que retorna as informações do usuário atualmente
    autenticado, extraído do token JWT no header Authorization ou cookie.

    Como efeito colateral, re-emite o cookie HTTPOnly se a request veio
    via header Authorization sem cookie correspondente. Isso permite que
    sessões antigas (criadas antes do cookie existir) migrem
    silenciosamente assim que o usuário abre o app — sem precisar
    relogar para que <img src="/storage/..."> volte a funcionar.

    Args:
        request: Request usado para inspecionar cookies enviados.
        response: Response usado para emitir o cookie (migração).
        user: Usuário autenticado (injetado automaticamente via dependency).

    Returns:
        UsuarioRead: Dados públicos do usuário autenticado.

    Raises:
        AuthenticationError: Se o token é inválido, expirado ou ausente.

    Status Code:
        200: Sucesso com dados do usuário.
        401: Token não fornecido ou inválido.
    """
    if ACCESS_TOKEN_COOKIE not in request.cookies:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            set_access_cookie(response, auth_header.split(" ", 1)[1])
    return UsuarioRead.model_validate(user)


@router.put("/perfil", response_model=UsuarioRead)
@limiter.limit("10/minute")
async def atualizar_perfil(
    request: Request,
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
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="UPDATE",
        recurso="perfil",
        recurso_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)
    return UsuarioRead.model_validate(user)


@router.post("/perfil/foto", response_model=dict)
@limiter.limit("10/minute")
async def upload_foto_perfil(
    request: Request,
    foto: UploadFile = File(...),
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Faz upload da foto de perfil para o storage S3-compatible e atualiza foto_url do usuário.

    Args:
        foto: Arquivo de imagem enviado via multipart/form-data.
        user: Usuário autenticado.
        db: Sessão do banco de dados.

    Returns:
        dict: Objeto com campo foto_url contendo a URL pública da foto.

    Raises:
        AuthenticationError: Se token inválido.

    Status Code:
        200: Upload realizado com sucesso.
        401: Não autenticado.
    """
    file_bytes = await ler_upload_com_limite(foto, max_size=5 * 1024 * 1024)
    validar_magic_bytes_imagem(file_bytes)
    storage = StorageService.get()
    key = storage.generate_key("avatares", foto.filename or "foto.jpg")
    url = await storage.upload(file_bytes, key, content_type=foto.content_type or "image/jpeg")

    user.foto_url = url
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="UPDATE",
        recurso="perfil_foto",
        recurso_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)

    return {"foto_url": url}
