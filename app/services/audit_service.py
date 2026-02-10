import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        usuario_id: int,
        acao: str,
        recurso: str,
        recurso_id: int | None = None,
        detalhes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        entry = AuditLog(
            usuario_id=usuario_id,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            detalhes=json.dumps(detalhes, ensure_ascii=False) if detalhes else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
