from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Repository genérico com CRUD básico, soft delete e multi-tenancy."""

    def __init__(self, model: type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> T | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        guarnicao_id: int | None = None,
    ) -> Sequence[T]:
        query = select(self.model)

        if hasattr(self.model, "ativo"):
            query = query.where(self.model.ativo == True)  # noqa: E712

        if guarnicao_id is not None and hasattr(self.model, "guarnicao_id"):
            query = query.where(self.model.guarnicao_id == guarnicao_id)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, obj: T, data: dict) -> T:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def soft_delete(self, obj: T, deleted_by_id: int | None = None) -> T:
        if hasattr(obj, "ativo"):
            obj.ativo = False
            obj.desativado_em = datetime.now(UTC)
            if deleted_by_id is not None:
                obj.desativado_por_id = deleted_by_id
            await self.db.flush()
        return obj
