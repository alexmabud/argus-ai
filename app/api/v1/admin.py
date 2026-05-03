"""Router de administração — gestão de usuários pelo admin.

Fornece endpoints restritos a administradores para criar usuários
com senha de uso único, pausar/excluir acesso e gerar novas senhas.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import (
    EquipeCreate,
    EquipeIsolamentoUpdate,
    EquipeRead,
    SenhaGeradaResponse,
    UsuarioAdminCreate,
    UsuarioAdminRead,
    UsuarioMoverEquipe,
)
from app.schemas.bpm import BpmCreate, BpmRead
from app.services.audit_service import AuditService
from app.services.bpm_service import BpmService
from app.services.equipe_service import EquipeService
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
@limiter.limit("30/minute")
async def listar_usuarios(
    request: Request,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UsuarioAdminRead]:
    """Lista todos os usuários ativos do sistema (todas as equipes e sem equipe).

    Retorna todos os usuários, não apenas os da equipe do admin. O frontend
    agrupa por guarnicao_id (incluindo None = "Sem Equipe").

    Args:
        request: Requisição HTTP.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de usuários com status de sessão, ordenada por nome.

    Status Code:
        200: Lista retornada com sucesso.
        403: Usuário não é administrador.
    """
    service = UsuarioAdminService(db)
    usuarios = await service.listar_todos()
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
@limiter.limit("10/minute")
async def criar_usuario(
    request: Request,
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
            guarnicao_id=data.guarnicao_id,
        )
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    audit = AuditService(db)
    await audit.log(
        usuario_id=admin.id,
        acao="CREATE",
        recurso="usuario",
        recurso_id=usuario.id,
        detalhes={"matricula": data.matricula},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario.id, matricula=usuario.matricula, senha=senha)


@router.patch("/usuarios/{usuario_id}/pausar", response_model=dict)
@limiter.limit("10/minute")
async def pausar_usuario(
    request: Request,
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
    audit = AuditService(db)
    await audit.log(
        usuario_id=admin.id,
        acao="UPDATE",
        recurso="usuario",
        recurso_id=usuario_id,
        detalhes={"acao": "pausar"},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "mensagem": "Usuário pausado com sucesso"}


@router.post("/usuarios/{usuario_id}/gerar-senha", response_model=SenhaGeradaResponse)
@limiter.limit("10/minute")
async def gerar_nova_senha(
    request: Request,
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
    audit = AuditService(db)
    await audit.log(
        usuario_id=admin.id,
        acao="UPDATE",
        recurso="usuario",
        recurso_id=usuario_id,
        detalhes={"acao": "gerar_nova_senha"},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario_id, matricula=matricula, senha=senha)


@router.delete("/usuarios/{usuario_id}", status_code=204)
@limiter.limit("10/minute")
async def excluir_usuario(
    request: Request,
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
    audit = AuditService(db)
    await audit.log(
        usuario_id=admin.id,
        acao="DELETE",
        recurso="usuario",
        recurso_id=usuario_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


@router.get("/bpms", response_model=list[BpmRead])
@limiter.limit("30/minute")
async def listar_bpms(
    request: Request,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[BpmRead]:
    """Lista todos os BPMs ativos.

    Args:
        request: Requisição HTTP.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de BpmRead ordenada por nome.

    Status Code:
        200: Lista retornada com sucesso.
        403: Não é administrador.
    """
    service = BpmService(db)
    bpms = await service.listar_bpms()
    return [BpmRead.model_validate(b) for b in bpms]


@router.post("/bpms", response_model=BpmRead, status_code=201)
@limiter.limit("10/minute")
async def criar_bpm(
    request: Request,
    data: BpmCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BpmRead:
    """Cria novo BPM.

    Args:
        request: Requisição HTTP.
        data: Nome do BPM.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        BpmRead com ID atribuído.

    Raises:
        HTTPException: 409 se nome já existe.

    Status Code:
        201: BPM criado com sucesso.
        403: Não é administrador.
        409: Nome de BPM já cadastrado.
    """
    service = BpmService(db)
    try:
        bpm = await service.criar_bpm(nome=data.nome, admin_id=admin.id)
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    await db.commit()
    return BpmRead.model_validate(bpm)


@router.get("/equipes", response_model=list[EquipeRead])
@limiter.limit("30/minute")
async def listar_equipes(
    request: Request,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[EquipeRead]:
    """Lista todas as equipes ativas para gestão pelo admin.

    Args:
        request: Requisição HTTP.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de EquipeRead ordenada por nome.

    Status Code:
        200: Lista retornada com sucesso.
        403: Não é administrador.
    """
    service = EquipeService(db)
    equipes = await service.listar_equipes()
    return [EquipeRead.model_validate(e) for e in equipes]


@router.post("/equipes", response_model=EquipeRead, status_code=201)
@limiter.limit("10/minute")
async def criar_equipe(
    request: Request,
    data: EquipeCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EquipeRead:
    """Cria nova equipe (guarnição) com código gerado automaticamente.

    Args:
        request: Requisição HTTP.
        data: Nome e bpm_id da equipe.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        EquipeRead com ID e código atribuídos.

    Raises:
        HTTPException: 409 se nome já existe.

    Status Code:
        201: Equipe criada com sucesso.
        403: Não é administrador.
        409: Nome de equipe já cadastrado.
    """
    service = EquipeService(db)
    try:
        equipe = await service.criar_equipe(nome=data.nome, bpm_id=data.bpm_id, admin_id=admin.id)
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    await db.commit()
    await db.refresh(equipe)
    return EquipeRead.model_validate(equipe)


@router.patch("/equipes/{guarnicao_id}/toggle-isolamento", response_model=EquipeRead)
@limiter.limit("10/minute")
async def toggle_isolamento_equipe(
    request: Request,
    guarnicao_id: int,
    data: EquipeIsolamentoUpdate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EquipeRead:
    """Liga ou desliga o isolamento de abordagens para a equipe.

    Quando ativo, membros da equipe veem apenas as abordagens da própria
    equipe. Quando inativo (padrão), veem todas as abordagens do sistema.
    Pessoas abordadas permanecem visíveis para todos independentemente.

    Args:
        request: Requisição HTTP.
        guarnicao_id: ID da equipe a atualizar.
        data: Novo valor do toggle.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        EquipeRead com o novo valor de isolamento_abordagens.

    Raises:
        HTTPException: 404 se a equipe não existe ou está inativa.

    Status Code:
        200: Toggle atualizado com sucesso.
        403: Não é administrador.
        404: Equipe não encontrada.
    """
    service = EquipeService(db)
    try:
        equipe = await service.toggle_isolamento(
            guarnicao_id=guarnicao_id,
            valor=data.isolamento_abordagens,
            admin_id=admin.id,
        )
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return EquipeRead.model_validate(equipe)


@router.patch("/usuarios/{usuario_id}/equipe", response_model=UsuarioAdminRead)
@limiter.limit("10/minute")
async def mover_usuario_equipe(
    request: Request,
    usuario_id: int,
    data: UsuarioMoverEquipe,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UsuarioAdminRead:
    """Move o usuário para outra equipe ou remove de equipe (guarnicao_id=None).

    Args:
        request: Requisição HTTP.
        usuario_id: ID do usuário a mover.
        data: Equipe de destino (guarnicao_id) ou None para remover de equipe.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        UsuarioAdminRead com guarnicao_id atualizado.

    Raises:
        HTTPException: 404 se o usuário não existe.

    Status Code:
        200: Usuário movido com sucesso.
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        usuario = await service.mover_equipe(
            usuario_id=usuario_id,
            guarnicao_id_destino=data.guarnicao_id,
            admin_id=admin.id,
        )
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return UsuarioAdminRead(
        id=usuario.id,
        nome=usuario.nome,
        matricula=usuario.matricula,
        posto_graduacao=usuario.posto_graduacao,
        nome_guerra=usuario.nome_guerra,
        foto_url=usuario.foto_url,
        is_admin=usuario.is_admin,
        ativo=usuario.ativo,
        tem_sessao=usuario.session_id is not None,
        guarnicao_id=usuario.guarnicao_id,
    )
