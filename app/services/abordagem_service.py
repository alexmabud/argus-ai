"""Serviço de lógica de negócio para Abordagem.

Gerencia criação completa de abordagens com vinculação de pessoas,
veículos, passagens, geocoding reverso, PostGIS e materialização
de relacionamentos entre pessoas abordadas juntas. Centraliza toda
a orquestração do fluxo de abordagem em campo, garantindo que o
cadastro completo ocorra em < 40 segundos.
"""

import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.models.abordagem import (
    Abordagem,
    AbordagemPassagem,
    AbordagemPessoa,
    AbordagemVeiculo,
)
from app.repositories.abordagem_repo import AbordagemRepository
from app.schemas.abordagem import AbordagemCreate, AbordagemUpdate
from app.services.audit_service import AuditService
from app.services.geocoding_service import GeocodingService
from app.services.relacionamento_service import RelacionamentoService

logger = logging.getLogger("argus")


class AbordagemService:
    """Serviço central de Abordagem com PostGIS e materialização de relacionamentos.

    Orquestra o ciclo de vida completo de uma abordagem: criação com deduplicação
    offline, geocoding reverso best-effort, vinculação de pessoas/veículos/passagens,
    materialização de relacionamentos entre pessoas abordadas juntas, busca
    geoespacial por raio (PostGIS ST_DWithin) e atualização parcial.

    Segue as convenções do projeto:
    - Usa flush() ao invés de commit() (transação controlada pelo caller).
    - Registra todas as mutações via AuditService.
    - Multi-tenancy por guarnicao_id em todas as queries.
    - Soft delete (ativo=True) aplicado automaticamente pelo repositório.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Abordagem com suporte PostGIS.
        audit: Serviço de auditoria para log de mutações (LGPD).
        geocoding: Serviço de geocoding reverso (Nominatim/Google).
        relacionamento: Serviço de materialização de vínculos entre pessoas.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de abordagem com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = AbordagemRepository(db)
        self.audit = AuditService(db)
        self.geocoding = GeocodingService()
        self.relacionamento = RelacionamentoService(db)

    async def criar(
        self,
        data: AbordagemCreate,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Abordagem:
        """Cria abordagem completa com vinculações e relacionamentos.

        Fluxo completo de criação em campo (< 40 segundos):
        1. Deduplicação por client_id (offline sync)
        2. Geocoding reverso best-effort se lat/lon sem endereco_texto
        3. Criar ponto PostGIS POINT(longitude latitude)
        4. Criar registro Abordagem
        5. Vincular pessoas (AbordagemPessoa)
        6. Vincular veículos (AbordagemVeiculo)
        7. Vincular passagens (AbordagemPassagem com pessoa_id)
        8. Materializar relacionamentos se 2+ pessoas
        9. Audit log

        Args:
            data: Dados da abordagem (pessoas, veículos, passagens, coordenadas).
            user_id: ID do oficial que realizou a abordagem.
            guarnicao_id: ID da guarnição (multi-tenancy).
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Abordagem criada com ID atribuído e vinculações realizadas.
        """
        # 1. Deduplicação por client_id (offline sync)
        if data.client_id:
            existing = await self.repo.get_by_client_id(data.client_id)
            if existing:
                return existing

        # 2. Geocoding reverso best-effort
        endereco_texto = data.endereco_texto
        if not endereco_texto and data.latitude and data.longitude:
            try:
                endereco_texto = await self.geocoding.reverse(data.latitude, data.longitude)
            except Exception:
                logger.warning("Geocoding falhou, continuando sem endereço")

        # 3. Ponto PostGIS POINT(longitude latitude)
        localizacao = None
        if data.latitude is not None and data.longitude is not None:
            localizacao = f"POINT({data.longitude} {data.latitude})"

        # 4. Criar registro Abordagem
        abordagem = Abordagem(
            data_hora=data.data_hora,
            latitude=data.latitude,
            longitude=data.longitude,
            localizacao=localizacao,
            endereco_texto=endereco_texto,
            observacao=data.observacao,
            usuario_id=user_id,
            guarnicao_id=guarnicao_id,
            origem=data.origem,
            client_id=data.client_id,
        )
        self.db.add(abordagem)
        await self.db.flush()

        # 5. Vincular pessoas (AbordagemPessoa)
        for pessoa_id in data.pessoa_ids:
            self.db.add(
                AbordagemPessoa(
                    abordagem_id=abordagem.id,
                    pessoa_id=pessoa_id,
                )
            )

        # 6. Vincular veículos (AbordagemVeiculo)
        for veiculo_id in data.veiculo_ids:
            self.db.add(
                AbordagemVeiculo(
                    abordagem_id=abordagem.id,
                    veiculo_id=veiculo_id,
                )
            )

        # 7. Vincular passagens (AbordagemPassagem com pessoa_id)
        for passagem_vinculo in data.passagens:
            self.db.add(
                AbordagemPassagem(
                    abordagem_id=abordagem.id,
                    pessoa_id=passagem_vinculo.pessoa_id,
                    passagem_id=passagem_vinculo.passagem_id,
                )
            )

        await self.db.flush()

        # 8. Materializar relacionamentos se 2+ pessoas
        if len(data.pessoa_ids) > 1:
            await self.relacionamento.registrar_vinculo(
                data.pessoa_ids, abordagem.id, data.data_hora
            )

        # 9. Audit log
        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="abordagem",
            recurso_id=abordagem.id,
            detalhes={
                "pessoas": len(data.pessoa_ids),
                "veiculos": len(data.veiculo_ids),
                "origem": data.origem,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return abordagem

    async def buscar_por_id(
        self,
        abordagem_id: int,
        guarnicao_id: int,
    ) -> Abordagem:
        """Busca abordagem por ID com filtro multi-tenant.

        Retorna a abordagem se pertencer à guarnição informada e estiver ativa.

        Args:
            abordagem_id: Identificador da abordagem.
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Abordagem encontrada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
        """
        abordagem = await self.repo.get(abordagem_id)
        if not abordagem or abordagem.guarnicao_id != guarnicao_id:
            raise NaoEncontradoError("Abordagem")
        if not abordagem.ativo:
            raise NaoEncontradoError("Abordagem")
        return abordagem

    async def buscar_detalhe(
        self,
        abordagem_id: int,
        guarnicao_id: int,
    ) -> Abordagem:
        """Busca abordagem com todos os relacionamentos carregados (eager load).

        Carrega pessoas, veículos, fotos, passagens e ocorrências em uma
        única query usando selectinload. Ideal para tela de detalhe.

        Args:
            abordagem_id: Identificador da abordagem.
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Abordagem com todos os relacionamentos carregados.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
        """
        abordagem = await self.repo.get_detail(abordagem_id, guarnicao_id)
        if not abordagem:
            raise NaoEncontradoError("Abordagem")
        return abordagem

    async def listar(
        self,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Abordagem]:
        """Lista abordagens da guarnição com paginação.

        Retorna abordagens ativas ordenadas por data/hora decrescente,
        filtradas pela guarnição do usuário autenticado.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular (padrão 0).
            limit: Número máximo de resultados (padrão 20).

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        return await self.repo.list_by_guarnicao(guarnicao_id, skip, limit)

    async def buscar_por_raio(
        self,
        latitude: float,
        longitude: float,
        raio_metros: int,
        guarnicao_id: int,
        limit: int = 50,
    ) -> Sequence[Abordagem]:
        """Busca abordagens por raio geográfico usando PostGIS ST_DWithin.

        Retorna abordagens ativas dentro do raio especificado a partir de um
        ponto central, filtradas pela guarnição. Utiliza índice GiST em
        localizacao para performance otimizada.

        Args:
            latitude: Latitude do ponto central da busca.
            longitude: Longitude do ponto central da busca.
            raio_metros: Raio de busca em metros.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            limit: Número máximo de resultados (padrão 50).

        Returns:
            Sequência de Abordagens dentro do raio, ordenadas por data_hora.
        """
        return await self.repo.search_by_radius(
            latitude, longitude, raio_metros, guarnicao_id, limit
        )

    async def atualizar(
        self,
        abordagem_id: int,
        data: AbordagemUpdate,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Abordagem:
        """Atualiza campos editáveis de uma abordagem existente.

        Apenas campos de texto (observacao, endereco_texto) são editáveis
        pós-criação. Coordenadas e vinculações não são alteradas por este método.

        Args:
            abordagem_id: Identificador da abordagem a atualizar.
            data: Dados de atualização parcial (observacao, endereco_texto).
            user_id: ID do oficial que realizou a atualização.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Abordagem atualizada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
        """
        abordagem = await self.buscar_por_id(abordagem_id, guarnicao_id)

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self.repo.update(abordagem, update_data)

        await self.audit.log(
            usuario_id=user_id,
            acao="UPDATE",
            recurso="abordagem",
            recurso_id=abordagem.id,
            detalhes={"campos_atualizados": list(update_data.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return abordagem

    async def vincular_pessoa(
        self,
        abordagem_id: int,
        pessoa_id: int,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AbordagemPessoa:
        """Vincula uma pessoa a uma abordagem existente.

        Cria registro de associação AbordagemPessoa e re-materializa
        relacionamentos entre todas as pessoas da abordagem.

        Args:
            abordagem_id: Identificador da abordagem.
            pessoa_id: Identificador da pessoa a vincular.
            user_id: ID do oficial que realizou a vinculação.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            AbordagemPessoa criada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
        """
        abordagem = await self.buscar_detalhe(abordagem_id, guarnicao_id)

        vinculo = AbordagemPessoa(
            abordagem_id=abordagem.id,
            pessoa_id=pessoa_id,
        )
        self.db.add(vinculo)
        await self.db.flush()

        # Re-materializar relacionamentos com todas as pessoas da abordagem
        pessoa_ids_existentes = [ap.pessoa_id for ap in abordagem.pessoas]
        todas_pessoa_ids = list(set(pessoa_ids_existentes + [pessoa_id]))
        if len(todas_pessoa_ids) > 1:
            await self.relacionamento.registrar_vinculo(
                todas_pessoa_ids, abordagem.id, abordagem.data_hora
            )

        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="abordagem_pessoa",
            recurso_id=vinculo.id,
            detalhes={
                "abordagem_id": abordagem_id,
                "pessoa_id": pessoa_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return vinculo

    async def desvincular_pessoa(
        self,
        abordagem_id: int,
        pessoa_id: int,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove vínculo de pessoa com abordagem (soft delete da associação).

        Busca e remove a associação AbordagemPessoa entre a abordagem e a pessoa.
        Não afeta os relacionamentos materializados já existentes.

        Args:
            abordagem_id: Identificador da abordagem.
            pessoa_id: Identificador da pessoa a desvincular.
            user_id: ID do oficial que realizou a desvinculação.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Raises:
            NaoEncontradoError: Se abordagem não existe, não pertence à guarnição,
                ou pessoa não está vinculada a ela.
        """
        abordagem = await self.buscar_detalhe(abordagem_id, guarnicao_id)

        vinculo = next(
            (ap for ap in abordagem.pessoas if ap.pessoa_id == pessoa_id),
            None,
        )
        if not vinculo:
            raise NaoEncontradoError("Vínculo pessoa-abordagem")

        await self.db.delete(vinculo)
        await self.db.flush()

        await self.audit.log(
            usuario_id=user_id,
            acao="DELETE",
            recurso="abordagem_pessoa",
            recurso_id=vinculo.id,
            detalhes={
                "abordagem_id": abordagem_id,
                "pessoa_id": pessoa_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def vincular_veiculo(
        self,
        abordagem_id: int,
        veiculo_id: int,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AbordagemVeiculo:
        """Vincula um veículo a uma abordagem existente.

        Cria registro de associação AbordagemVeiculo.

        Args:
            abordagem_id: Identificador da abordagem.
            veiculo_id: Identificador do veículo a vincular.
            user_id: ID do oficial que realizou a vinculação.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            AbordagemVeiculo criada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
        """
        abordagem = await self.buscar_por_id(abordagem_id, guarnicao_id)

        vinculo = AbordagemVeiculo(
            abordagem_id=abordagem.id,
            veiculo_id=veiculo_id,
        )
        self.db.add(vinculo)
        await self.db.flush()

        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="abordagem_veiculo",
            recurso_id=vinculo.id,
            detalhes={
                "abordagem_id": abordagem_id,
                "veiculo_id": veiculo_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return vinculo

    async def desvincular_veiculo(
        self,
        abordagem_id: int,
        veiculo_id: int,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove vínculo de veículo com abordagem.

        Busca e remove a associação AbordagemVeiculo entre a abordagem e o veículo.

        Args:
            abordagem_id: Identificador da abordagem.
            veiculo_id: Identificador do veículo a desvincular.
            user_id: ID do oficial que realizou a desvinculação.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Raises:
            NaoEncontradoError: Se abordagem não existe, não pertence à guarnição,
                ou veículo não está vinculado a ela.
        """
        abordagem = await self.buscar_detalhe(abordagem_id, guarnicao_id)

        vinculo = next(
            (av for av in abordagem.veiculos if av.veiculo_id == veiculo_id),
            None,
        )
        if not vinculo:
            raise NaoEncontradoError("Vínculo veículo-abordagem")

        await self.db.delete(vinculo)
        await self.db.flush()

        await self.audit.log(
            usuario_id=user_id,
            acao="DELETE",
            recurso="abordagem_veiculo",
            recurso_id=vinculo.id,
            detalhes={
                "abordagem_id": abordagem_id,
                "veiculo_id": veiculo_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
