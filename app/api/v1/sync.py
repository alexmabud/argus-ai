"""Router de sincronização offline → online.

Fornece endpoint para receber batch de itens criados offline
pelo frontend PWA e processá-los com deduplicação por client_id.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user_with_guarnicao
from app.models.usuario import Usuario
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse
from app.services.audit_service import AuditService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post("/batch", response_model=SyncBatchResponse)
@limiter.limit("10/minute")
async def sync_batch(
    request: Request,
    data: SyncBatchRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user_with_guarnicao),
) -> SyncBatchResponse:
    """Recebe batch de itens criados offline e processa.

    Usa client_id para deduplicação (idempotente). Cada item
    é processado independentemente — falha de um não afeta os demais.
    Exige guarnicao_id atribuído (achado #18/2026-07-13): sem isso, os
    handlers internos de sincronização não conseguem criar registros
    multi-tenant, e a falha antes chegava como AssertionError não tratado
    em vez de auto-atribuição da guarnição padrão.

    Args:
        data: Batch de itens para sincronizar.
        db: Sessão do banco de dados.
        user: Usuário autenticado, com guarnição garantidamente atribuída.

    Returns:
        SyncBatchResponse com resultado por item.
    """
    service = SyncService(db)
    results = await service.process_batch(data.items, user)
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="SYNC",
        recurso="sync_batch",
        detalhes={"total_items": len(data.items), "resultados": len(results)},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return SyncBatchResponse(results=results)
