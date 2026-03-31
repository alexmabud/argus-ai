"""Repository de Localidade — queries de autocomplete e busca hierárquica.

Provê acesso aos dados de localidades (estados, cidades, bairros)
com suporte a autocomplete por texto e busca por nome normalizado.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.localidade import Localidade


class LocalidadeRepository:
    """Repository para operações de leitura e criação de localidades.

    Attributes:
        db: Sessão assíncrona do banco de dados.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Inicializa o repository com a sessão do banco.

        Args:
            db: Sessão assíncrona SQLAlchemy.
        """
        self.db = db

    async def listar_estados(self) -> list[Localidade]:
        """Retorna todos os estados ativos ordenados por nome de exibição.

        Returns:
            Lista de Localidade com tipo='estado', ordenada por nome_exibicao.
        """
        result = await self.db.execute(
            select(Localidade)
            .where(Localidade.tipo == "estado", Localidade.ativo.is_(True))
            .order_by(Localidade.nome_exibicao)
        )
        return list(result.scalars().all())

    async def autocomplete(
        self,
        tipo: str,
        parent_id: int,
        q: str,
        limit: int = 10,
    ) -> list[Localidade]:
        """Retorna localidades filtradas por texto (autocomplete).

        Busca pelo campo `nome` normalizado com ILIKE para ignorar case.
        Filtra por tipo e parent_id para garantir hierarquia correta.

        Args:
            tipo: Tipo da localidade ('cidade' ou 'bairro').
            parent_id: ID da localidade pai (estado para cidades, cidade para bairros).
            q: Texto de busca (mínimo 2 chars recomendado).
            limit: Número máximo de resultados (padrão: 10).

        Returns:
            Lista de até `limit` localidades que correspondem ao texto.
        """
        result = await self.db.execute(
            select(Localidade)
            .where(
                Localidade.tipo == tipo,
                Localidade.parent_id == parent_id,
                Localidade.ativo.is_(True),
                Localidade.nome.ilike(f"%{q}%"),
            )
            .order_by(Localidade.nome_exibicao)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def buscar_por_nome_e_parent(
        self,
        nome_normalizado: str,
        tipo: str,
        parent_id: int,
    ) -> Localidade | None:
        """Busca localidade exata por nome normalizado e parent (evita duplicatas).

        Args:
            nome_normalizado: Nome já normalizado (sem acento, minúsculas).
            tipo: Tipo da localidade ('cidade' ou 'bairro').
            parent_id: ID da localidade pai.

        Returns:
            Localidade encontrada ou None.
        """
        result = await self.db.execute(
            select(Localidade).where(
                Localidade.nome == nome_normalizado,
                Localidade.tipo == tipo,
                Localidade.parent_id == parent_id,
                Localidade.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get(self, localidade_id: int) -> Localidade | None:
        """Busca localidade por ID.

        Args:
            localidade_id: ID da localidade.

        Returns:
            Localidade encontrada ou None.
        """
        result = await self.db.execute(
            select(Localidade).where(
                Localidade.id == localidade_id,
                Localidade.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()
