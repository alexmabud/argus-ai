"""Serviço de lógica de negócio para vínculo direto pessoa-veículo.

Gerencia associação manual entre pessoa e veículo (independente de
abordagem), incluindo reativação de vínculos soft-deleted e listagem
unificada de veículos de uma pessoa (diretos + derivados de abordagem).
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.permissions import TenantFilter, assert_pode_remover_vinculo_veiculo
from app.models.pessoa_veiculo import PessoaVeiculo
from app.models.usuario import Usuario
from app.repositories.pessoa_repo import PessoaRepository
from app.repositories.pessoa_veiculo_repo import PessoaVeiculoRepository
from app.repositories.veiculo_repo import VeiculoRepository
from app.services.audit_service import AuditService


class PessoaVeiculoService:
    """Serviço de vínculo direto pessoa-veículo.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de PessoaVeiculo.
        pessoa_repo: Repositório de Pessoa (validação de existência/tenant).
        veiculo_repo: Repositório de Veiculo (validação + veículos via abordagem).
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de vínculo pessoa-veículo.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = PessoaVeiculoRepository(db)
        self.pessoa_repo = PessoaRepository(db)
        self.veiculo_repo = VeiculoRepository(db)
        self.audit = AuditService(db)

    async def vincular(
        self,
        pessoa_id: int,
        veiculo_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaVeiculo:
        """Cria (ou reativa) vínculo direto entre pessoa e veículo.

        Se já existir um vínculo soft-deleted para o mesmo par, reativa em
        vez de tentar inserir de novo — evita o erro de unique constraint
        que ocorreria ao criar uma segunda linha pro mesmo par.

        Args:
            pessoa_id: ID da pessoa.
            veiculo_id: ID do veículo.
            user: Usuário autenticado (tenant + auditoria).
            ip_address: IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            PessoaVeiculo criado ou reativado.

        Raises:
            NaoEncontradoError: Se pessoa ou veículo não existem.
            AcessoNegadoError: Se pessoa ou veículo pertencem a outra guarnição.
            ConflitoDadosError: Se o vínculo já está ativo.
        """
        pessoa = await self.pessoa_repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        veiculo = await self.veiculo_repo.get(veiculo_id)
        if not veiculo:
            raise NaoEncontradoError("Veículo")
        TenantFilter.check_ownership(veiculo, user)

        existente = await self.repo.get_par(pessoa_id, veiculo_id, include_inactive=True)
        if existente:
            if existente.ativo:
                raise ConflitoDadosError("Veículo já vinculado a esta pessoa")
            existente.ativo = True
            existente.desativado_em = None
            existente.desativado_por_id = None
            existente.criado_por_id = user.id
            await self.db.flush()
            vinculo = existente
        else:
            vinculo = PessoaVeiculo(
                pessoa_id=pessoa_id,
                veiculo_id=veiculo_id,
                criado_por_id=user.id,
                guarnicao_id=user.guarnicao_id,
            )
            # Atribui o relacionamento diretamente (não só o FK veiculo_id):
            # um teste anterior presumiu que vinculo.veiculo resolveria via
            # identity map sem query, mas isso se mostrou falso em produção
            # (MissingGreenlet real, confirmado via reprodução manual) —
            # setar o objeto aqui evita qualquer lazy-load posterior, já que
            # `veiculo` já foi carregado (e tem seu dono confirmado) acima.
            vinculo.veiculo = veiculo
            self.db.add(vinculo)
            try:
                await self.db.flush()
            except IntegrityError:
                # Corrida entre duas requisições vinculando o mesmo par pela
                # primeira vez: nenhuma via get_par (include_inactive=True)
                # ainda não existia, mas o INSERT perdedor colide com a
                # unique constraint. Mesmo tratamento de pessoa_service.py
                # (criar_vinculo_manual) para o cenário equivalente.
                await self.db.rollback()
                raise ConflitoDadosError("Veículo já vinculado a esta pessoa")

        await self.audit.log(
            usuario_id=user.id,
            acao="CREATE",
            recurso="pessoa_veiculo",
            recurso_id=vinculo.id,
            detalhes={"pessoa_id": pessoa_id, "veiculo_id": veiculo_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return vinculo

    async def desvincular(
        self,
        pessoa_id: int,
        veiculo_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove (soft delete) o vínculo direto entre pessoa e veículo.

        Não apaga o Veiculo em si — só desfaz a associação direta. Só afeta
        vínculos criados via este caminho (não toca em AbordagemVeiculo).

        Args:
            pessoa_id: ID da pessoa.
            veiculo_id: ID do veículo.
            user: Usuário autenticado (tenant + auditoria).
            ip_address: IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Raises:
            NaoEncontradoError: Se não existe vínculo direto ativo pro par.
            AcessoNegadoError: Se o vínculo pertence a outra guarnição, ou se
                o usuário não é quem criou o vínculo nem admin/super-admin.
        """
        vinculo = await self.repo.get_par(pessoa_id, veiculo_id, include_inactive=False)
        if not vinculo:
            raise NaoEncontradoError("Vínculo pessoa-veículo")
        TenantFilter.check_ownership(vinculo, user)
        assert_pode_remover_vinculo_veiculo(user, vinculo)

        await self.repo.soft_delete(vinculo, deleted_by_id=user.id)

        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="pessoa_veiculo",
            recurso_id=vinculo.id,
            detalhes={"pessoa_id": pessoa_id, "veiculo_id": veiculo_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def listar_veiculos_pessoa(self, pessoa_id: int, user: Usuario) -> list[dict]:
        """Lista veículos da pessoa, unificando vínculo direto e via abordagem.

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado (verificação de tenant).

        Returns:
            Lista de dicts {"veiculo": Veiculo, "origem": "direto"|"abordagem",
            "criado_por_id": int|None}. Quando o mesmo veículo tem as duas
            origens, prevalece "direto" (permite exibir o botão de
            desvincular). "criado_por_id" identifica quem criou o vínculo
            direto (None para vínculo só via abordagem, ou vínculo direto
            legado sem autor registrado) — usado pelo frontend para decidir
            se mostra a opção de remover (dono do vínculo ou admin).

        Raises:
            NaoEncontradoError: Se a pessoa não existe.
            AcessoNegadoError: Se a pessoa pertence a outra guarnição.
        """
        pessoa = await self.pessoa_repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        via_abordagem = await self.veiculo_repo.get_veiculos_por_pessoa_via_abordagem(pessoa_id)
        diretos = await self.repo.listar_diretos(pessoa_id)

        merged: dict[int, dict] = {
            v.id: {"veiculo": v, "origem": "abordagem", "criado_por_id": None}
            for v in via_abordagem
        }
        for pv in diretos:
            merged[pv.veiculo_id] = {
                "veiculo": pv.veiculo,
                "origem": "direto",
                "criado_por_id": pv.criado_por_id,
            }

        return list(merged.values())
