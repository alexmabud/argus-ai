"""Repositório para PessoaVeiculo — vínculo direto pessoa-veículo."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pessoa_veiculo import PessoaVeiculo
from app.models.veiculo import Veiculo
from app.repositories.base import BaseRepository


class PessoaVeiculoRepository(BaseRepository[PessoaVeiculo]):
    """Repositório de PessoaVeiculo com busca por par e listagem ativa.

    Attributes:
        model: Classe PessoaVeiculo.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de PessoaVeiculo.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(PessoaVeiculo, db)

    async def get_par(
        self, pessoa_id: int, veiculo_id: int, include_inactive: bool = False
    ) -> PessoaVeiculo | None:
        """Busca o vínculo entre uma pessoa e um veículo específicos.

        Args:
            pessoa_id: ID da pessoa.
            veiculo_id: ID do veículo.
            include_inactive: Se True, inclui vínculos soft-deleted (usado
                para reativar em vez de duplicar).

        Returns:
            PessoaVeiculo encontrado ou None.
        """
        query = select(PessoaVeiculo).where(
            PessoaVeiculo.pessoa_id == pessoa_id,
            PessoaVeiculo.veiculo_id == veiculo_id,
        )
        if not include_inactive:
            query = query.where(PessoaVeiculo.ativo == True)  # noqa: E712
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def listar_diretos(self, pessoa_id: int) -> Sequence[PessoaVeiculo]:
        """Lista vínculos diretos ativos de uma pessoa, com veículo carregado.

        Exclui vínculos cujo Veiculo esteja soft-deletado — mesma checagem
        já aplicada no caminho via abordagem
        (`VeiculoRepository.get_veiculos_por_pessoa_via_abordagem`), pra que
        os dois caminhos que se unificam em `listar_veiculos_pessoa` tenham
        paridade defensiva (hoje não há rota de desativar veículo, mas o
        service já existe — `VeiculoService.desativar` — então evita uma
        inconsistência silenciosa se essa rota for exposta no futuro).

        Args:
            pessoa_id: ID da pessoa.

        Returns:
            Sequência de PessoaVeiculo ativos, com veículo ativo.
        """
        query = (
            select(PessoaVeiculo)
            .join(Veiculo, Veiculo.id == PessoaVeiculo.veiculo_id)
            .where(
                PessoaVeiculo.pessoa_id == pessoa_id,
                PessoaVeiculo.ativo == True,  # noqa: E712
                Veiculo.ativo == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
