"""Router de Localidades — autocomplete e criação de cidades/bairros.

Expõe endpoints para listar estados, buscar cidades/bairros por texto
(autocomplete) e cadastrar novas localidades sem duplicatas.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.localidade import LocalidadeCreate, LocalidadeRead
from app.services.audit_service import AuditService
from app.services.localidade_service import LocalidadeService

router = APIRouter(prefix="/localidades", tags=["Localidades"])


@router.get("", response_model=list[LocalidadeRead])
@limiter.limit("30/minute")
async def listar_localidades(
    request: Request,
    tipo: str = Query(..., pattern="^(estado|cidade|bairro)$"),
    parent_id: int | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list:
    """Lista estados ou faz autocomplete de cidades/bairros.

    Para tipo='estado': retorna todos os 27 estados (ignora parent_id e q).
    Para tipo='cidade' ou 'bairro': quando q ausente lista todos os filhos do
    parent_id (até 200); quando q fornecido filtra por texto (1+ caractere).

    Args:
        tipo: Nível hierárquico — 'estado', 'cidade' ou 'bairro'.
        parent_id: ID da localidade pai (obrigatório para cidade e bairro).
        q: Texto de busca opcional (sem mínimo de caracteres).
        db: Sessão do banco de dados.
        _: Usuário autenticado (apenas para proteger o endpoint).

    Returns:
        Lista de localidades correspondentes.

    Raises:
        HTTPException 400: Quando parent_id ausente para cidade/bairro.
    """
    service = LocalidadeService(db)

    if tipo == "estado":
        return await service.listar_estados()

    if parent_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_id é obrigatório para cidade e bairro.",
        )

    return await service.autocomplete(tipo=tipo, parent_id=parent_id, q=q)


@router.post("", response_model=LocalidadeRead, status_code=201)
@limiter.limit("10/minute")
async def criar_localidade(
    request: Request,
    data: LocalidadeCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> LocalidadeRead:
    """Cadastra nova cidade ou bairro.

    Valida hierarquia e impede duplicatas. Normaliza o nome para busca.
    Estados não podem ser criados via API (são fixos no seed).

    Args:
        data: Dados da nova localidade (nome, tipo, parent_id).
        db: Sessão do banco de dados.
        _: Usuário autenticado.

    Returns:
        Localidade criada com id e nome_exibicao.

    Raises:
        HTTPException 404: Parent não encontrado.
        HTTPException 400: Hierarquia inválida.
        ConflitoDadosError 409: Duplicata detectada.
    """
    service = LocalidadeService(db)
    localidade = await service.criar(data)
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="localidade",
        recurso_id=localidade.id,
        detalhes={"nome": data.nome, "tipo": data.tipo},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(localidade)
    return LocalidadeRead.model_validate(localidade)
