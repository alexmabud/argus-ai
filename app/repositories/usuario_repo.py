from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, db: AsyncSession):
        super().__init__(Usuario, db)

    async def get_by_matricula(self, matricula: str) -> Usuario | None:
        result = await self.db.execute(
            select(Usuario).where(
                Usuario.matricula == matricula,
                Usuario.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Usuario | None:
        result = await self.db.execute(
            select(Usuario).where(
                Usuario.email == email,
                Usuario.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
