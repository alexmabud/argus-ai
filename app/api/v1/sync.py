"""Router de sincronização offline → online.

Fornece endpoint para receber batch de itens criados offline
pelo frontend PWA e processá-los com deduplicação por client_id.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post("/batch", response_model=SyncBatchResponse)
async def sync_batch(
    data: SyncBatchRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> SyncBatchResponse:
    """Recebe batch de itens criados offline e processa.

    Usa client_id para deduplicação (idempotente). Cada item
    é processado independentemente — falha de um não afeta os demais.

    Args:
        data: Batch de itens para sincronizar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        SyncBatchResponse com resultado por item.
    """
    service = SyncService(db)
    results = await service.process_batch(data.items, user)
    return SyncBatchResponse(results=results)
