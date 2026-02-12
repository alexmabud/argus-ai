"""Repositório para materialização de relacionamentos entre pessoas.

Implementa UPSERT (INSERT ON CONFLICT DO UPDATE) para manter vínculos
atualizados entre pessoas abordadas juntas, com frequência e histórico.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relacionamento import RelacionamentoPessoa


class RelacionamentoRepository:
    """Repositório para operações de RelacionamentoPessoa.

    Implementa UPSERT para materializar vínculos entre pessoas,
    incrementando frequência quando já existem, e busca de vínculos
    em ambas direções.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Relacionamento.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db

    async def upsert(
        self,
        pessoa_id_a: int,
        pessoa_id_b: int,
        abordagem_id: int,
        data_hora: datetime,
    ) -> None:
        """Cria ou atualiza vínculo entre duas pessoas (UPSERT).

        Se o vínculo não existe, cria com frequencia=1.
        Se já existe, incrementa frequencia e atualiza ultima_vez/ultima_abordagem_id.
        Garante que pessoa_id_a < pessoa_id_b para evitar duplicatas.

        Args:
            pessoa_id_a: ID da primeira pessoa.
            pessoa_id_b: ID da segunda pessoa.
            abordagem_id: ID da abordagem que gerou o vínculo.
            data_hora: Data/hora da abordagem.
        """
        # Garantir ordenação: pessoa_id_a < pessoa_id_b
        id_a = min(pessoa_id_a, pessoa_id_b)
        id_b = max(pessoa_id_a, pessoa_id_b)

        stmt = insert(RelacionamentoPessoa).values(
            pessoa_id_a=id_a,
            pessoa_id_b=id_b,
            frequencia=1,
            primeira_abordagem_id=abordagem_id,
            ultima_abordagem_id=abordagem_id,
            primeira_vez=data_hora,
            ultima_vez=data_hora,
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_relacionamento",
            set_={
                "frequencia": RelacionamentoPessoa.frequencia + 1,
                "ultima_abordagem_id": abordagem_id,
                "ultima_vez": data_hora,
            },
        )

        await self.db.execute(stmt)
        await self.db.flush()

    async def get_vinculos(self, pessoa_id: int) -> Sequence[RelacionamentoPessoa]:
        """Obtém todos os vínculos de uma pessoa (ambas direções).

        Busca relacionamentos onde a pessoa aparece como pessoa_a ou pessoa_b,
        ordenados por frequência decrescente (vínculos mais fortes primeiro).

        Args:
            pessoa_id: ID da pessoa para buscar vínculos.

        Returns:
            Sequência de RelacionamentoPessoa ordenada por frequência decrescente.
        """
        query = (
            select(RelacionamentoPessoa)
            .where(
                or_(
                    RelacionamentoPessoa.pessoa_id_a == pessoa_id,
                    RelacionamentoPessoa.pessoa_id_b == pessoa_id,
                )
            )
            .order_by(RelacionamentoPessoa.frequencia.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
