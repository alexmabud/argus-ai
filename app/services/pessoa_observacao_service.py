"""Serviço de lógica de negócio para observações de pessoas.

Gerencia criação, listagem, atualização e soft delete de observações
vinculadas a pessoas, com verificação de tenant e auditoria.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, NaoEncontradoError
from app.core.permissions import TenantFilter
from app.models.pessoa import Pessoa
from app.models.pessoa_observacao import PessoaObservacao
from app.models.usuario import Usuario
from app.repositories.base import BaseRepository
from app.schemas.pessoa_observacao import PessoaObservacaoCreate, PessoaObservacaoUpdate
from app.services.audit_service import AuditService


class PessoaObservacaoService:
    """Serviço de observações de pessoas.

    Gerencia o ciclo de vida de observações vinculadas a pessoas abordadas.
    Verifica isolamento de tenant em todas as operações e registra auditoria
    em todas as mutações.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        pessoa_repo: Repositório base para Pessoa.
        obs_repo: Repositório base para PessoaObservacao.
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de observações.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.pessoa_repo = BaseRepository(Pessoa, db)
        self.obs_repo = BaseRepository(PessoaObservacao, db)
        self.audit = AuditService(db)

    async def _get_pessoa_verificado(self, pessoa_id: int, user: Usuario) -> Pessoa:
        """Busca pessoa verificando existência e tenant.

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado.

        Returns:
            Pessoa encontrada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.pessoa_repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa não encontrada.")
        TenantFilter.check_ownership(pessoa, user)
        return pessoa

    async def listar(self, pessoa_id: int, user: Usuario) -> list[PessoaObservacao]:
        """Lista observações ativas de uma pessoa, ordenadas da mais recente.

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado.

        Returns:
            Lista de PessoaObservacao ativas, ordenadas por criado_em desc.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa de outra guarnição.
        """
        await self._get_pessoa_verificado(pessoa_id, user)
        result = await self.db.execute(
            select(PessoaObservacao)
            .where(
                PessoaObservacao.pessoa_id == pessoa_id,
                PessoaObservacao.ativo == True,  # noqa: E712
            )
            .order_by(PessoaObservacao.criado_em.desc(), PessoaObservacao.id.desc())
        )
        return list(result.scalars().all())

    async def criar(
        self,
        pessoa_id: int,
        data: PessoaObservacaoCreate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaObservacao:
        """Cria nova observação vinculada a uma pessoa.

        Args:
            pessoa_id: ID da pessoa.
            data: Dados da observação (texto).
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).
            user_agent: User-Agent do cliente (para auditoria).

        Returns:
            PessoaObservacao criada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa de outra guarnição.
        """
        await self._get_pessoa_verificado(pessoa_id, user)
        obs = PessoaObservacao(
            pessoa_id=pessoa_id,
            texto=data.texto,
            guarnicao_id=user.guarnicao_id,
        )
        await self.obs_repo.create(obs)
        await self.audit.log(
            usuario_id=user.id,
            acao="CREATE",
            recurso="pessoa_observacao",
            recurso_id=obs.id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return obs

    async def atualizar(
        self,
        obs_id: int,
        pessoa_id: int,
        data: PessoaObservacaoUpdate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaObservacao:
        """Atualiza o texto de uma observação existente.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID da pessoa dona da observação.
            data: Novo texto da observação.
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).
            user_agent: User-Agent do cliente (para auditoria).

        Returns:
            PessoaObservacao atualizada.

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self._get_obs_verificada(obs_id, pessoa_id, user)
        await self.obs_repo.update(obs, {"texto": data.texto})
        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="pessoa_observacao",
            recurso_id=obs_id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return obs

    async def deletar(
        self,
        obs_id: int,
        pessoa_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Soft delete de uma observação.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID da pessoa dona da observação.
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).
            user_agent: User-Agent do cliente (para auditoria).

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self._get_obs_verificada(obs_id, pessoa_id, user)
        await self.obs_repo.soft_delete(obs, deleted_by_id=user.id)
        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="pessoa_observacao",
            recurso_id=obs_id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _get_obs_verificada(
        self, obs_id: int, pessoa_id: int, user: Usuario
    ) -> PessoaObservacao:
        """Busca observação verificando existência, vínculo com pessoa e tenant.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID esperado da pessoa dona.
            user: Usuário autenticado.

        Returns:
            PessoaObservacao encontrada.

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self.obs_repo.get(obs_id)
        if not obs or obs.pessoa_id != pessoa_id:
            raise NaoEncontradoError("Observação não encontrada.")
        if obs.guarnicao_id != user.guarnicao_id:
            raise AcessoNegadoError("Acesso negado.")
        return obs
