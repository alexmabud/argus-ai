"""Serviço para materialização de relacionamentos entre pessoas.

Gerencia criação e consulta de vínculos materializados entre pessoas
abordadas juntas, usando UPSERT para incrementar frequência e manter
histórico temporal. Materializar vínculos evita queries N:N complexas
e permite análise de rede social entre abordados.
"""

from datetime import datetime
from itertools import combinations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relacionamento import RelacionamentoPessoa
from app.repositories.relacionamento_repo import RelacionamentoRepository


class RelacionamentoService:
    """Serviço de Relacionamento para materializar vínculos entre pessoas.

    Cria e consulta vínculos materializados entre pessoas abordadas juntas.
    Para cada abordagem com N pessoas, gera C(N,2) pares únicos via UPSERT,
    incrementando frequência quando o par já existe. Garante ordenação
    (pessoa_id_a < pessoa_id_b) para evitar duplicatas.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Relacionamento com suporte a UPSERT.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de relacionamento.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = RelacionamentoRepository(db)

    async def registrar_vinculo(
        self,
        pessoa_ids: list[int],
        abordagem_id: int,
        data_hora: datetime,
    ) -> None:
        """Materializa vínculos entre todas as combinações de pessoas.

        Para N pessoas, cria C(N,2) pares usando UPSERT no banco.
        Exemplo: 3 pessoas [A, B, C] gera pares (A,B), (A,C), (B,C).
        Se o par já existe, incrementa frequência e atualiza ultima_vez.

        Args:
            pessoa_ids: IDs das pessoas abordadas juntas.
            abordagem_id: ID da abordagem que gerou os vínculos.
            data_hora: Data/hora da abordagem para registro temporal.
        """
        unique_ids = sorted(set(pessoa_ids))
        for id_a, id_b in combinations(unique_ids, 2):
            await self.repo.upsert(id_a, id_b, abordagem_id, data_hora)

    async def buscar_vinculos(self, pessoa_id: int) -> list[RelacionamentoPessoa]:
        """Obtém todos os vínculos de uma pessoa.

        Busca relacionamentos onde a pessoa aparece como pessoa_a ou pessoa_b,
        permitindo análise completa de rede social do abordado.

        Args:
            pessoa_id: ID da pessoa para buscar vínculos.

        Returns:
            Lista de RelacionamentoPessoa ordenada por frequência decrescente
            (vínculos mais fortes primeiro).
        """
        return list(await self.repo.get_vinculos(pessoa_id))
