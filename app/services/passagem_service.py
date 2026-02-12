"""Serviço de lógica de negócio para Passagem (tipo penal/infração).

Gerencia criação, busca e listagem de passagens criminais e infrações
administrativas, com verificação de unicidade por combinação (lei, artigo)
e busca textual por nome de crime.
"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.passagem import Passagem
from app.repositories.passagem_repo import PassagemRepository
from app.schemas.passagem import PassagemCreate
from app.services.audit_service import AuditService


class PassagemService:
    """Serviço de Passagem para catálogo de tipos penais.

    Implementa lógica de negócio para gerenciamento do catálogo de passagens
    criminais e infrações administrativas. Passagens são dados de referência
    (catálogo) compartilhados entre guarnições, sem multi-tenancy.
    NÃO importa ou depende de FastAPI.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Passagem com busca por lei/artigo.
        audit: Serviço de auditoria para registro de ações.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de Passagem.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = PassagemRepository(db)
        self.audit = AuditService(db)

    async def criar(
        self,
        data: PassagemCreate,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Passagem:
        """Cria nova passagem criminal com verificação de unicidade.

        Verifica se combinação (lei, artigo) já existe antes de criar.
        Passagens são dados de catálogo compartilhados entre guarnições.

        Args:
            data: Dados de criação (lei, artigo, nome_crime).
            user_id: ID do usuário que está criando o registro.
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Passagem criada com ID atribuído pelo banco.

        Raises:
            ConflitoDadosError: Se combinação (lei, artigo) já existe.
        """
        existing = await self.repo.get_by_lei_artigo(data.lei, data.artigo)
        if existing:
            raise ConflitoDadosError(f"Passagem já cadastrada: {data.lei} art. {data.artigo}")

        passagem = Passagem(
            lei=data.lei,
            artigo=data.artigo,
            nome_crime=data.nome_crime,
        )

        await self.repo.create(passagem)

        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="passagem",
            recurso_id=passagem.id,
            detalhes={
                "lei": data.lei,
                "artigo": data.artigo,
                "nome_crime": data.nome_crime,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return passagem

    async def buscar_por_id(self, passagem_id: int) -> Passagem:
        """Obtém passagem por ID.

        Passagens são dados de catálogo sem filtro de guarnição.

        Args:
            passagem_id: ID da passagem a buscar.

        Returns:
            Passagem encontrada.

        Raises:
            NaoEncontradoError: Se passagem não existe.
        """
        passagem = await self.repo.get(passagem_id)
        if not passagem:
            raise NaoEncontradoError("Passagem")
        return passagem

    async def buscar(
        self,
        lei: str | None = None,
        artigo: str | None = None,
        nome_crime: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Passagem]:
        """Busca passagens com filtros combinados.

        Delega para PassagemRepository.search() que combina filtros
        com AND. Nome de crime usa ILIKE para busca parcial.

        Args:
            lei: Filtro por lei (busca exata, opcional).
            artigo: Filtro por artigo (busca exata, opcional).
            nome_crime: Filtro por nome do crime (busca parcial ILIKE, opcional).
            skip: Número de registros a pular (paginação).
            limit: Número máximo de resultados.

        Returns:
            Sequência de passagens que satisfazem os filtros.
        """
        return await self.repo.search(
            lei=lei,
            artigo=artigo,
            nome_crime=nome_crime,
            skip=skip,
            limit=limit,
        )
