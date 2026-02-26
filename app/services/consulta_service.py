"""Serviço de consulta unificada cross-domain.

Implementa busca simultânea em pessoas (fuzzy nome + CPF hash),
veículos (placa parcial) e abordagens (endereço texto ILIKE),
consolidando resultados em uma única resposta.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import hash_for_search
from app.models.abordagem import Abordagem
from app.models.usuario import Usuario
from app.repositories.abordagem_repo import AbordagemRepository
from app.repositories.pessoa_repo import PessoaRepository
from app.repositories.veiculo_repo import VeiculoRepository


class ConsultaService:
    """Serviço de consulta unificada para busca cross-domain.

    Permite busca simultânea em múltiplas entidades (pessoa, veículo,
    abordagem) através de um único termo de busca, consolidando
    resultados com paginação. Aplica filtros multi-tenant automaticamente.
    NÃO importa ou depende de FastAPI.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        pessoa_repo: Repositório de Pessoa para busca fuzzy e CPF hash.
        veiculo_repo: Repositório de Veículo para busca por placa.
        abordagem_repo: Repositório de Abordagem para busca por endereço.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de consulta unificada.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.pessoa_repo = PessoaRepository(db)
        self.veiculo_repo = VeiculoRepository(db)
        self.abordagem_repo = AbordagemRepository(db)

    async def busca_unificada(
        self,
        q: str,
        tipo: str | None = None,
        skip: int = 0,
        limit: int = 20,
        user: Usuario | None = None,
    ) -> dict:
        """Busca unificada em pessoa, veículo e abordagem.

        Distribui a busca conforme o tipo solicitado ou busca em todas
        as entidades simultaneamente. Aplica filtros multi-tenant via
        guarnicao_id do usuário autenticado.

        Estratégias de busca por entidade:
        - Pessoa: busca fuzzy por nome (pg_trgm) + busca exata por CPF (hash SHA-256).
        - Veículo: busca parcial por placa (ILIKE normalizado).
        - Abordagem: busca por endereço texto (ILIKE).

        Args:
            q: Termo de busca (nome, CPF, placa ou endereço).
            tipo: Tipo de entidade para filtrar ("pessoa", "veiculo", "abordagem").
                Se None, busca em todas as entidades.
            skip: Número de registros a pular por entidade (paginação).
            limit: Número máximo de resultados por entidade.
            user: Usuário autenticado (para filtro multi-tenant).

        Returns:
            Dicionário com chaves "pessoas", "veiculos", "abordagens"
            e "total_resultados" com a contagem combinada.
        """
        guarnicao_id = user.guarnicao_id if user else None
        pessoas = []
        veiculos = []
        abordagens = []

        if tipo is None or tipo == "pessoa":
            pessoas = await self._buscar_pessoas(q, guarnicao_id, skip, limit)

        if tipo is None or tipo == "veiculo":
            veiculos = await self._buscar_veiculos(q, guarnicao_id, skip, limit)

        if tipo is None or tipo == "abordagem":
            abordagens = await self._buscar_abordagens(q, guarnicao_id, skip, limit)

        return {
            "pessoas": pessoas,
            "veiculos": veiculos,
            "abordagens": abordagens,
            "total_resultados": len(pessoas) + len(veiculos) + len(abordagens),
        }

    async def _buscar_pessoas(
        self,
        q: str,
        guarnicao_id: int | None,
        skip: int,
        limit: int,
    ) -> list:
        """Busca pessoas por nome (fuzzy) e CPF (hash).

        Tenta busca fuzzy por nome via pg_trgm. Se o termo parecer
        um CPF (contém apenas dígitos, pontos e traços), também tenta
        busca exata por hash SHA-256.

        Args:
            q: Termo de busca (nome ou CPF).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de pessoas encontradas (sem duplicatas).
        """
        resultados = []
        ids_vistos = set()

        # Busca fuzzy por nome
        fuzzy_results = await self.pessoa_repo.search_by_nome_fuzzy(
            q, guarnicao_id, skip=skip, limit=limit
        )
        for pessoa in fuzzy_results:
            if pessoa.id not in ids_vistos:
                resultados.append(pessoa)
                ids_vistos.add(pessoa.id)

        # Se parece CPF (só dígitos, pontos e traços), busca por hash
        cpf_clean = q.replace(".", "").replace("-", "").replace(" ", "")
        if cpf_clean.isdigit() and len(cpf_clean) >= 6:
            cpf_hash = hash_for_search(q)
            pessoa_cpf = await self.pessoa_repo.get_by_cpf_hash(cpf_hash, guarnicao_id)
            if pessoa_cpf and pessoa_cpf.id not in ids_vistos:
                resultados.append(pessoa_cpf)

        return resultados

    async def _buscar_veiculos(
        self,
        q: str,
        guarnicao_id: int | None,
        skip: int,
        limit: int,
    ) -> list:
        """Busca veículos por placa parcial (ILIKE).

        Normaliza o termo de busca (uppercase, sem traços) e delega
        para o repositório de veículo com busca parcial.

        Args:
            q: Termo de busca (placa parcial ou completa).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de veículos encontrados.
        """
        return list(
            await self.veiculo_repo.search_by_placa_partial(q, guarnicao_id, skip=skip, limit=limit)
        )

    async def _buscar_abordagens(
        self,
        q: str,
        guarnicao_id: int | None,
        skip: int,
        limit: int,
    ) -> list:
        """Busca abordagens por endereço texto (ILIKE).

        Realiza busca parcial no campo endereco_texto da abordagem,
        filtrando por guarnição e registros ativos.

        Args:
            q: Termo de busca (parte do endereço).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de abordagens encontradas.
        """
        query = select(Abordagem).where(
            Abordagem.ativo == True,  # noqa: E712
            Abordagem.endereco_texto.ilike(f"%{q}%"),
        )
        if guarnicao_id is not None:
            query = query.where(Abordagem.guarnicao_id == guarnicao_id)

        query = query.order_by(Abordagem.data_hora.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
