"""Router de administração — gestão de usuários pelo admin.

Fornece endpoints restritos a administradores para criar usuários
com senha de uso único, pausar/excluir acesso e gerar novas senhas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import SenhaGeradaResponse, UsuarioAdminCreate, UsuarioAdminRead
from app.services.usuario_admin_service import UsuarioAdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(user: Usuario = Depends(get_current_user)) -> Usuario:
    """Dependência que exige que o usuário seja administrador.

    Args:
        user: Usuário autenticado (injetado automaticamente).

    Returns:
        Usuário autenticado e administrador.

    Raises:
        HTTPException: 403 se o usuário não for administrador.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user


@router.get("/usuarios", response_model=list[UsuarioAdminRead])
async def listar_usuarios(
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UsuarioAdminRead]:
    """Lista todos os usuários ativos e pausados da guarnição do admin.

    Args:
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de usuários com status de sessão.

    Status Code:
        200: Lista retornada com sucesso.
        403: Usuário não é administrador.
    """
    service = UsuarioAdminService(db)
    usuarios = await service.listar_usuarios(admin.guarnicao_id)
    return [
        UsuarioAdminRead(
            id=u.id,
            nome=u.nome,
            matricula=u.matricula,
            posto_graduacao=u.posto_graduacao,
            nome_guerra=u.nome_guerra,
            foto_url=u.foto_url,
            is_admin=u.is_admin,
            ativo=u.ativo,
            tem_sessao=u.session_id is not None,
            guarnicao_id=u.guarnicao_id,
        )
        for u in usuarios
    ]


@router.post("/usuarios", response_model=SenhaGeradaResponse, status_code=201)
async def criar_usuario(
    data: UsuarioAdminCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SenhaGeradaResponse:
    """Cria novo usuário com senha de uso único gerada automaticamente.

    A senha é exibida uma única vez na resposta. O admin deve entregá-la
    pessoalmente ao usuário. Após o primeiro login, a senha é invalidada.

    Args:
        data: Dados de criação (apenas matrícula).
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        SenhaGeradaResponse: ID, matrícula e senha gerada (plain text, única vez).

    Raises:
        HTTPException: 409 se matrícula já cadastrada.

    Status Code:
        201: Usuário criado com sucesso.
        403: Não é administrador.
        409: Matrícula já existe.
    """
    service = UsuarioAdminService(db)
    try:
        usuario, senha = await service.criar_usuario(
            matricula=data.matricula,
            admin_id=admin.id,
            guarnicao_id=admin.guarnicao_id,
        )
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario.id, matricula=usuario.matricula, senha=senha)


@router.patch("/usuarios/{usuario_id}/pausar", response_model=dict)
async def pausar_usuario(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pausa o acesso do usuário desconectando-o imediatamente.

    Limpa o session_id do usuário no banco. O próximo request do usuário
    retornará 401. O usuário precisará de nova senha para retornar.

    Args:
        usuario_id: ID do usuário a pausar.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Mensagem de confirmação.

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        200: Usuário pausado com sucesso.
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        await service.pausar_usuario(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return {"ok": True, "mensagem": "Usuário pausado com sucesso"}


@router.post("/usuarios/{usuario_id}/gerar-senha", response_model=SenhaGeradaResponse)
async def gerar_nova_senha(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SenhaGeradaResponse:
    """Gera nova senha de uso único para o usuário, invalidando a sessão atual.

    Args:
        usuario_id: ID do usuário.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        SenhaGeradaResponse: Nova senha em plain text (exibir apenas uma vez).

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        200: Nova senha gerada com sucesso.
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        senha, matricula = await service.gerar_nova_senha(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario_id, matricula=matricula, senha=senha)


@router.delete("/usuarios/{usuario_id}", status_code=204)
async def excluir_usuario(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Exclui logicamente o usuário (soft delete — dados preservados por LGPD).

    Args:
        usuario_id: ID do usuário a excluir.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        204: Usuário excluído com sucesso (sem corpo).
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        await service.excluir_usuario(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
