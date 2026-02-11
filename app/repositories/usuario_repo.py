"""Repositório específico para operações com o modelo Usuario.

Fornece métodos de consulta especializados para buscar usuários por matrícula
ou email, com filtros de atividade integrados.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    """Repositório para acesso a dados de usuários (agentes).

    Estende BaseRepository com métodos específicos para buscar usuários por
    matrícula ou email. Garante que apenas usuários ativos sejam retornados
    em todas as consultas.

    Attributes:
        model: Sempre Usuario.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Usuario, db)

    async def get_by_matricula(self, matricula: str) -> Usuario | None:
        """Obtém um usuário pela matrícula.

        Busca um usuário ativo que possua a matrícula especificada.

        Args:
            matricula: Matrícula do agente (identificador único por guarnição).

        Returns:
            Objeto Usuario se encontrado e ativo, None caso contrário.
        """
        result = await self.db.execute(
            select(Usuario).where(
                Usuario.matricula == matricula,
                Usuario.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Usuario | None:
        """Obtém um usuário pelo email.

        Busca um usuário ativo que possua o email especificado.

        Args:
            email: Email do usuário.

        Returns:
            Objeto Usuario se encontrado e ativo, None caso contrário.
        """
        result = await self.db.execute(
            select(Usuario).where(
                Usuario.email == email,
                Usuario.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
