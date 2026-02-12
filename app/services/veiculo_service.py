"""Serviço de lógica de negócio para Veículo.

Gerencia criação, atualização, busca e soft delete de veículos,
com normalização de placa, verificação de unicidade e auditoria
de todas as mutações.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.permissions import TenantFilter
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo
from app.repositories.veiculo_repo import VeiculoRepository
from app.schemas.veiculo import VeiculoCreate, VeiculoUpdate
from app.services.audit_service import AuditService


class VeiculoService:
    """Serviço de Veículo com normalização de placa e busca parcial.

    Implementa lógica de negócio para gerenciamento de veículos registrados
    em abordagens, incluindo normalização automática de placa (uppercase,
    sem traços), verificação de unicidade global e busca parcial via ILIKE.
    NÃO importa ou depende de FastAPI.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Veículo com busca por placa.
        audit: Serviço de auditoria para registro de ações.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de Veículo.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = VeiculoRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def _normalizar_placa(placa: str) -> str:
        """Normaliza placa para formato padrão (uppercase, sem traços/espaços).

        Args:
            placa: Placa informada pelo usuário.

        Returns:
            Placa normalizada em uppercase sem caracteres especiais.
        """
        return placa.upper().replace("-", "").replace(" ", "")

    async def criar(
        self,
        data: VeiculoCreate,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Veiculo:
        """Cria novo veículo com normalização de placa.

        Normaliza a placa para uppercase sem traços e verifica unicidade
        global antes de criar. Registra evento de auditoria.

        Args:
            data: Dados de criação do veículo (placa, modelo, cor, etc).
            user_id: ID do usuário que está criando o registro.
            guarnicao_id: ID da guarnição para isolamento multi-tenant.
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Veículo criado com ID atribuído pelo banco.

        Raises:
            ConflitoDadosError: Se placa já cadastrada no sistema.
        """
        placa_normalizada = self._normalizar_placa(data.placa)

        existing = await self.repo.get_by_placa(placa_normalizada)
        if existing:
            raise ConflitoDadosError("Veículo com esta placa já cadastrado")

        veiculo = Veiculo(
            placa=placa_normalizada,
            modelo=data.modelo,
            cor=data.cor,
            ano=data.ano,
            tipo=data.tipo,
            observacoes=data.observacoes,
            guarnicao_id=guarnicao_id,
        )

        await self.repo.create(veiculo)

        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="veiculo",
            recurso_id=veiculo.id,
            detalhes={"placa": placa_normalizada},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return veiculo

    async def atualizar(
        self,
        veiculo_id: int,
        data: VeiculoUpdate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Veiculo:
        """Atualiza veículo existente com verificação de tenant.

        Placa não pode ser alterada (imutável após criação).
        Registra campos alterados na auditoria.

        Args:
            veiculo_id: ID do veículo a atualizar.
            data: Dados de atualização parcial (modelo, cor, ano, tipo, obs).
            user: Usuário autenticado (para verificação de tenant).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Veículo atualizado.

        Raises:
            NaoEncontradoError: Se veículo não existe.
            AcessoNegadoError: Se veículo pertence a outra guarnição.
        """
        veiculo = await self.repo.get(veiculo_id)
        if not veiculo:
            raise NaoEncontradoError("Veículo")
        TenantFilter.check_ownership(veiculo, user)

        update_data = data.model_dump(exclude_unset=True)

        await self.repo.update(veiculo, update_data)

        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="veiculo",
            recurso_id=veiculo.id,
            detalhes={"campos_alterados": list(update_data.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return veiculo

    async def buscar_por_id(self, veiculo_id: int, user: Usuario) -> Veiculo:
        """Obtém veículo por ID com verificação de tenant.

        Args:
            veiculo_id: ID do veículo a buscar.
            user: Usuário autenticado (para verificação de guarnição).

        Returns:
            Veículo encontrado.

        Raises:
            NaoEncontradoError: Se veículo não existe.
            AcessoNegadoError: Se veículo pertence a outra guarnição.
        """
        veiculo = await self.repo.get(veiculo_id)
        if not veiculo:
            raise NaoEncontradoError("Veículo")
        TenantFilter.check_ownership(veiculo, user)
        return veiculo

    async def buscar(
        self,
        placa: str | None = None,
        modelo: str | None = None,
        cor: str | None = None,
        skip: int = 0,
        limit: int = 20,
        user: Usuario | None = None,
    ) -> list:
        """Busca veículos por placa (parcial), modelo, cor ou lista paginada.

        Despacha para o método de busca apropriado conforme os filtros:
        - Placa informada: busca parcial via ILIKE (normalizada).
        - Sem filtros: lista paginada da guarnição.

        Args:
            placa: Placa parcial para busca ILIKE (opcional).
            modelo: Reservado para busca futura por modelo (opcional).
            cor: Reservado para busca futura por cor (opcional).
            skip: Número de registros a pular (paginação).
            limit: Número máximo de resultados.
            user: Usuário autenticado (para filtro multi-tenant).

        Returns:
            Lista de veículos encontrados.
        """
        if placa:
            return list(
                await self.repo.search_by_placa_partial(
                    placa, user.guarnicao_id, skip=skip, limit=limit
                )
            )

        return list(await self.repo.get_all(skip=skip, limit=limit, guarnicao_id=user.guarnicao_id))

    async def desativar(
        self,
        veiculo_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Veiculo:
        """Soft delete de veículo com auditoria.

        Marca veículo como inativo (ativo=False) sem remoção física.
        Registra data, usuário responsável e evento de auditoria.

        Args:
            veiculo_id: ID do veículo a desativar.
            user: Usuário autenticado (para verificação de tenant e auditoria).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Veículo desativado.

        Raises:
            NaoEncontradoError: Se veículo não existe.
            AcessoNegadoError: Se veículo pertence a outra guarnição.
        """
        veiculo = await self.repo.get(veiculo_id)
        if not veiculo:
            raise NaoEncontradoError("Veículo")
        TenantFilter.check_ownership(veiculo, user)

        await self.repo.soft_delete(veiculo, deleted_by_id=user.id)

        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="veiculo",
            recurso_id=veiculo.id,
            detalhes={"placa": veiculo.placa},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return veiculo
