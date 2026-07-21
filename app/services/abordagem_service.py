"""Serviço de lógica de negócio para Abordagem.

Gerencia criação completa de abordagens com vinculação de pessoas,
veículos, geocoding reverso, PostGIS e materialização
de relacionamentos entre pessoas abordadas juntas. Centraliza toda
a orquestração do fluxo de abordagem em campo, garantindo que o
cadastro completo ocorra em < 40 segundos.
"""

import logging
from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.permissions import assert_pode_editar_abordagem
from app.models.abordagem import (
    Abordagem,
    AbordagemPessoa,
    AbordagemVeiculo,
)
from app.models.usuario import Usuario
from app.repositories.abordagem_repo import AbordagemRepository
from app.schemas.abordagem import AbordagemCreate, AbordagemUpdate
from app.services.audit_service import AuditService
from app.services.geocoding_service import GeocodingService
from app.services.relacionamento_service import RelacionamentoService

logger = logging.getLogger("argus")


def filtro_abordagem(user: Usuario) -> tuple[int | None, int | None]:
    """Retorna (guarnicao_id, bpm_id) para filtro de escopo de abordagens.

    Prioridade: guarnição > BPM > global. Apenas um dos dois será não-None.
    Mesma regra usada por `GET /abordagens/{id}` e `GET /abordagens/` —
    reaproveitada por `AbordagemService.atualizar`/`vincular_pessoa`/
    `desvincular_pessoa`/`vincular_veiculo`/`desvincular_veiculo` para que
    essas ações respeitem o mesmo escopo que a visualização já respeita
    (achado em teste manual: antes, esses métodos filtravam direto por
    `user.guarnicao_id`, ignorando `isolamento_abordagens` — um admin cuja
    guarnição não tem isolamento ativado, o padrão do model, conseguia ver
    a abordagem de outra guarnição mas não conseguia editá-la).

    Args:
        user: Usuário autenticado com guarnicao e bpm carregados.

    Returns:
        Tupla (guarnicao_id, bpm_id). Ambos None = acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)


class AbordagemService:
    """Serviço central de Abordagem com PostGIS e materialização de relacionamentos.

    Orquestra o ciclo de vida completo de uma abordagem: criação com deduplicação
    offline, geocoding reverso best-effort, vinculação de pessoas/veículos,
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
        7. Materializar relacionamentos se 2+ pessoas
        8. Audit log

        Args:
            data: Dados da abordagem (pessoas, veículos, coordenadas).
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
        try:
            await self.db.flush()
        except IntegrityError:
            # Race: outra requisição concorrente inseriu o MESMO client_id entre o
            # dedup-check (passo 1) e este flush. O índice único parcial em
            # client_id rejeita o segundo insert — recupera a abordagem vencedora
            # e retorna (mantém a idempotência do sync offline sob concorrência).
            await self.db.rollback()
            if data.client_id:
                existing = await self.repo.get_by_client_id(data.client_id)
                if existing:
                    return existing
            raise

        # 5. Vincular pessoas (AbordagemPessoa)
        for pessoa_id in data.pessoa_ids:
            self.db.add(
                AbordagemPessoa(
                    abordagem_id=abordagem.id,
                    pessoa_id=pessoa_id,
                )
            )

        # 6. Vincular veículos (AbordagemVeiculo) com vínculo por pessoa se informado
        for veiculo_id in data.veiculo_ids:
            self.db.add(
                AbordagemVeiculo(
                    abordagem_id=abordagem.id,
                    veiculo_id=veiculo_id,
                    pessoa_id=data.veiculo_por_pessoa.get(veiculo_id),
                )
            )

        await self.db.flush()

        # 7. Materializar relacionamentos se 2+ pessoas
        if len(data.pessoa_ids) > 1:
            await self.relacionamento.registrar_vinculo(
                data.pessoa_ids, abordagem.id, data.data_hora
            )

        # 8. Audit log
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
        guarnicao_id: int | None,
        bpm_id: int | None = None,
    ) -> Abordagem:
        """Busca abordagem com todos os relacionamentos carregados (eager load).

        Carrega pessoas, veículos, fotos e ocorrências em uma
        única query usando selectinload. Ideal para tela de detalhe.
        Prioridade: guarnicao_id > bpm_id > global.

        Args:
            abordagem_id: Identificador da abordagem.
            guarnicao_id: ID da guarnição para filtro por equipe (prevalece).
            bpm_id: ID do BPM para filtro por BPM (usado se guarnicao_id=None).

        Returns:
            Abordagem com todos os relacionamentos carregados.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não está no escopo.
        """
        if guarnicao_id is not None:
            abordagem = await self.repo.get_detail(abordagem_id, guarnicao_id)
        elif bpm_id is not None:
            abordagem = await self.repo.get_detail_by_bpm(abordagem_id, bpm_id)
        else:
            abordagem = await self.repo.get_detail_global(abordagem_id)
        if not abordagem:
            raise NaoEncontradoError("Abordagem")
        return abordagem

    async def verificar_escopo(
        self,
        abordagem_id: int,
        guarnicao_id: int | None,
        bpm_id: int | None = None,
    ) -> None:
        """Verifica que a abordagem existe e está no escopo, sem carregar relacionamentos.

        Checagem de autorização leve para rotas/serviços que só precisam
        confirmar que uma abordagem_id pertence ao escopo do usuário antes de
        operar sobre ela (ex.: listar fotos, anexar uma ocorrência) — usar
        `buscar_detalhe` só para essa checagem descartava o eager load de 4
        relacionamentos em seguida (revisão pós-#22/2026-07-13).

        Args:
            abordagem_id: Identificador da abordagem.
            guarnicao_id: ID da guarnição para filtro por equipe (prevalece).
            bpm_id: ID do BPM para filtro por BPM (usado se guarnicao_id=None).

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não está no escopo.
        """
        if not await self.repo.existe_no_escopo(abordagem_id, guarnicao_id, bpm_id=bpm_id):
            raise NaoEncontradoError("Abordagem")

    async def listar(
        self,
        guarnicao_id: int | None,
        bpm_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Abordagem]:
        """Lista abordagens com paginação.

        Retorna abordagens ativas ordenadas por data/hora decrescente.
        Prioridade: guarnicao_id > bpm_id > global.

        Args:
            guarnicao_id: ID da guarnição (filtro por equipe, prevalece).
            bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).
            skip: Número de registros a pular (padrão 0).
            limit: Número máximo de resultados (padrão 20).

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        if guarnicao_id is not None:
            return await self.repo.list_by_guarnicao(guarnicao_id, skip, limit)
        if bpm_id is not None:
            return await self.repo.list_by_bpm(bpm_id, skip, limit)
        return await self.repo.list_global(skip, limit)

    async def listar_por_data(
        self,
        guarnicao_id: int | None,
        data: date,
        bpm_id: int | None = None,
    ) -> Sequence[Abordagem]:
        """Lista abordagens em uma data específica.

        Retorna todos os registros do dia sem paginação, com eager
        loading completo de pessoas, veículos, fotos e ocorrências.
        Prioridade: guarnicao_id > bpm_id > global.

        Args:
            guarnicao_id: ID da guarnição para filtro por equipe (prevalece).
            data: Data de referência (YYYY-MM-DD).
            bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).

        Returns:
            Sequência de Abordagens do dia ordenadas por data_hora decrescente.
        """
        if guarnicao_id is not None:
            return await self.repo.list_by_data(guarnicao_id, data)
        if bpm_id is not None:
            return await self.repo.list_by_data_by_bpm(bpm_id, data)
        return await self.repo.list_by_data_global(data)

    async def buscar_por_texto(
        self,
        q: str,
        guarnicao_id: int | None,
        bpm_id: int | None = None,
        limit: int = 100,
    ) -> Sequence[Abordagem]:
        """Busca abordagens por texto em todas as datas.

        Pesquisa por nome de pessoa abordada, placa, atributos do veículo
        (modelo, cor, tipo) ou endereço em texto livre, sem restrição de data.
        Prioridade: guarnicao_id > bpm_id > global.

        Args:
            q: Termo de busca.
            guarnicao_id: ID da guarnição para filtro por equipe (prevalece).
            bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).
            limit: Número máximo de resultados (padrão 100).

        Returns:
            Sequência de Abordagens que correspondem ao termo.
        """
        if guarnicao_id is not None:
            return await self.repo.search_by_texto(q, guarnicao_id, limit)
        if bpm_id is not None:
            return await self.repo.search_by_texto_by_bpm(bpm_id, q, limit)
        return await self.repo.search_by_texto_global(q, limit)

    async def listar_por_usuario(
        self,
        usuario_id: int,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Abordagem]:
        """Lista abordagens do usuário autenticado com paginação.

        Filtra pelo usuário logado (não toda a guarnição), com eager
        loading de pessoas, veículos, fotos e ocorrências.

        Args:
            usuario_id: ID do oficial autenticado.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Registros a pular (padrão 0).
            limit: Número máximo de resultados (padrão 20).

        Returns:
            Sequência de Abordagens com relacionamentos carregados.
        """
        return await self.repo.list_by_usuario(usuario_id, guarnicao_id, skip, limit)

    async def listar_por_pessoa(
        self,
        pessoa_id: int,
        guarnicao_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Abordagem]:
        """Lista abordagens de uma pessoa com relacionamentos (paginado no banco).

        Abordagens na ficha de uma pessoa são globais — sem filtro de guarnição.
        guarnicao_id aceito por compatibilidade mas sempre ignorado.

        Args:
            pessoa_id: ID da pessoa.
            guarnicao_id: Ignorado. Mantido por compatibilidade de assinatura.
            skip: Registros a pular (OFFSET).
            limit: Número máximo de resultados (LIMIT).

        Returns:
            Sequência de Abordagens com pessoas e veículos carregados.
        """
        return await self.repo.list_by_pessoa(pessoa_id, None, skip=skip, limit=limit)

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
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Abordagem:
        """Atualiza campos editáveis de uma abordagem existente.

        Apenas campos de texto (observacao, endereco_texto) são editáveis
        pós-criação. Coordenadas e vinculações não são alteradas por este método.
        Restrito a quem registrou a abordagem ou a um admin da guarnição.

        Args:
            abordagem_id: Identificador da abordagem a atualizar.
            data: Dados de atualização parcial (observacao, endereco_texto).
            user: Usuário autenticado que realiza a atualização.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Abordagem atualizada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
            AcessoNegadoError: Se o usuário não é dono da abordagem nem admin.
        """
        assert user.guarnicao_id is not None
        guarnicao_id_filtro, bpm_id_filtro = filtro_abordagem(user)
        abordagem = await self.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
        assert_pode_editar_abordagem(user, abordagem)

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self.repo.update(abordagem, update_data)

        await self.audit.log(
            usuario_id=user.id,
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
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Abordagem:
        """Vincula uma pessoa a uma abordagem existente.

        Cria registro de associação AbordagemPessoa (ou reativa um vínculo
        soft-deletado anterior) e re-materializa relacionamentos entre
        todas as pessoas ativas da abordagem. Restrito a quem registrou
        a abordagem ou a um admin da guarnição.

        Args:
            abordagem_id: Identificador da abordagem.
            pessoa_id: Identificador da pessoa a vincular.
            user: Usuário autenticado que realiza a vinculação.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Abordagem com a lista de pessoas atualizada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
            AcessoNegadoError: Se o usuário não é dono da abordagem nem admin.
            ConflitoDadosError: Se a pessoa já está vinculada (ativa) à abordagem.
        """
        assert user.guarnicao_id is not None
        guarnicao_id_filtro, bpm_id_filtro = filtro_abordagem(user)
        abordagem = await self.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
        assert_pode_editar_abordagem(user, abordagem)

        vinculo_existente = next(
            (ap for ap in abordagem.pessoas if ap.pessoa_id == pessoa_id), None
        )
        if vinculo_existente is not None and vinculo_existente.ativo:
            raise ConflitoDadosError("Pessoa já vinculada a esta abordagem")
        if vinculo_existente is not None:
            vinculo = vinculo_existente
            vinculo.ativo = True
            vinculo.desativado_em = None
            vinculo.desativado_por_id = None
            await self.db.flush()
        else:
            vinculo = AbordagemPessoa(
                abordagem_id=abordagem.id,
                pessoa_id=pessoa_id,
            )
            self.db.add(vinculo)
            try:
                await self.db.flush()
            except IntegrityError:
                # Corrida entre duas requisições vinculando a mesma pessoa pela
                # primeira vez: nenhum vínculo ainda existia na leitura acima,
                # mas o INSERT perdedor colide com a unique constraint. Mesmo
                # tratamento de pessoa_veiculo_service.py (vincular).
                await self.db.rollback()
                raise ConflitoDadosError("Pessoa já vinculada a esta abordagem")

        # Re-materializar relacionamentos com todas as pessoas ativas da abordagem
        pessoa_ids_existentes = [ap.pessoa_id for ap in abordagem.pessoas if ap.ativo]
        todas_pessoa_ids = list(set(pessoa_ids_existentes + [pessoa_id]))
        if len(todas_pessoa_ids) > 1:
            await self.relacionamento.registrar_vinculo(
                todas_pessoa_ids, abordagem.id, abordagem.data_hora
            )

        await self.audit.log(
            usuario_id=user.id,
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

        # db.refresh(attribute_names=["pessoas"]) não é suficiente aqui: recarrega
        # a coleção, mas não o relacionamento aninhado AbordagemPessoa.pessoa (que
        # buscar_detalhe carrega via selectinload encadeado) — o vínculo novo ficava
        # com .pessoa não carregado, e _serializar_detalhe (síncrono) batia em
        # MissingGreenlet ao tentar lazy-load fora do contexto async (achado ao
        # vivo em 2026-07-19: o vínculo era salvo no banco, só a resposta falhava).
        # expire() é obrigatório antes do re-fetch: sem isso, buscar_detalhe
        # encontra o objeto já na identity map e devolve a coleção antiga —
        # SQLAlchemy não reexecuta selectinload em relacionamento já carregado.
        self.db.expire(abordagem)
        return await self.buscar_detalhe(abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro)

    async def desvincular_pessoa(
        self,
        abordagem_id: int,
        pessoa_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove vínculo de pessoa com abordagem (soft delete da associação).

        Busca e remove a associação AbordagemPessoa entre a abordagem e a pessoa.
        Não afeta os relacionamentos materializados já existentes. Restrito a
        quem registrou a abordagem ou a um admin da guarnição.

        Args:
            abordagem_id: Identificador da abordagem.
            pessoa_id: Identificador da pessoa a desvincular.
            user: Usuário autenticado que realiza a desvinculação.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Raises:
            NaoEncontradoError: Se abordagem não existe, não pertence à guarnição,
                ou pessoa não está vinculada (ativa) a ela.
            AcessoNegadoError: Se o usuário não é dono da abordagem nem admin.
        """
        assert user.guarnicao_id is not None
        guarnicao_id_filtro, bpm_id_filtro = filtro_abordagem(user)
        abordagem = await self.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
        assert_pode_editar_abordagem(user, abordagem)

        vinculo = next(
            (ap for ap in abordagem.pessoas if ap.pessoa_id == pessoa_id and ap.ativo),
            None,
        )
        if not vinculo:
            raise NaoEncontradoError("Vínculo pessoa-abordagem")

        vinculo.ativo = False
        vinculo.desativado_em = datetime.now(UTC)
        vinculo.desativado_por_id = user.id
        await self.db.flush()

        await self.audit.log(
            usuario_id=user.id,
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
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Abordagem:
        """Vincula um veículo a uma abordagem existente.

        Cria registro de associação AbordagemVeiculo (ou reativa um vínculo
        soft-deletado anterior). Restrito a quem registrou a abordagem ou
        a um admin da guarnição.

        Args:
            abordagem_id: Identificador da abordagem.
            veiculo_id: Identificador do veículo a vincular.
            user: Usuário autenticado que realiza a vinculação.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Abordagem com a lista de veículos atualizada.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence à guarnição.
            AcessoNegadoError: Se o usuário não é dono da abordagem nem admin.
            ConflitoDadosError: Se o veículo já está vinculado (ativo) à abordagem.
        """
        assert user.guarnicao_id is not None
        guarnicao_id_filtro, bpm_id_filtro = filtro_abordagem(user)
        abordagem = await self.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
        assert_pode_editar_abordagem(user, abordagem)

        vinculo_existente = next(
            (av for av in abordagem.veiculos if av.veiculo_id == veiculo_id), None
        )
        if vinculo_existente is not None and vinculo_existente.ativo:
            raise ConflitoDadosError("Veículo já vinculado a esta abordagem")
        if vinculo_existente is not None:
            vinculo = vinculo_existente
            vinculo.ativo = True
            vinculo.desativado_em = None
            vinculo.desativado_por_id = None
            await self.db.flush()
        else:
            vinculo = AbordagemVeiculo(
                abordagem_id=abordagem.id,
                veiculo_id=veiculo_id,
            )
            self.db.add(vinculo)
            try:
                await self.db.flush()
            except IntegrityError:
                # Corrida entre duas requisições vinculando o mesmo veículo pela
                # primeira vez: nenhum vínculo ainda existia na leitura acima,
                # mas o INSERT perdedor colide com a unique constraint. Mesmo
                # tratamento de pessoa_veiculo_service.py (vincular).
                await self.db.rollback()
                raise ConflitoDadosError("Veículo já vinculado a esta abordagem")

        await self.audit.log(
            usuario_id=user.id,
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

        # Mesmo motivo do db.refresh trocado por buscar_detalhe em vincular_pessoa:
        # refresh(attribute_names=[...]) não recarrega o relacionamento aninhado
        # (AbordagemVeiculo.veiculo), causando MissingGreenlet em _serializar_detalhe.
        # expire() força buscar_detalhe a reexecutar o selectinload em vez de
        # devolver a coleção antiga já carregada na identity map.
        self.db.expire(abordagem)
        return await self.buscar_detalhe(abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro)

    async def desvincular_veiculo(
        self,
        abordagem_id: int,
        veiculo_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove vínculo de veículo com abordagem.

        Busca e remove a associação AbordagemVeiculo entre a abordagem e o
        veículo. Restrito a quem registrou a abordagem ou a um admin da
        guarnição.

        Args:
            abordagem_id: Identificador da abordagem.
            veiculo_id: Identificador do veículo a desvincular.
            user: Usuário autenticado que realiza a desvinculação.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Raises:
            NaoEncontradoError: Se abordagem não existe, não pertence à guarnição,
                ou veículo não está vinculado (ativo) a ela.
            AcessoNegadoError: Se o usuário não é dono da abordagem nem admin.
        """
        assert user.guarnicao_id is not None
        guarnicao_id_filtro, bpm_id_filtro = filtro_abordagem(user)
        abordagem = await self.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
        assert_pode_editar_abordagem(user, abordagem)

        vinculo = next(
            (av for av in abordagem.veiculos if av.veiculo_id == veiculo_id and av.ativo),
            None,
        )
        if not vinculo:
            raise NaoEncontradoError("Vínculo veículo-abordagem")

        vinculo.ativo = False
        vinculo.desativado_em = datetime.now(UTC)
        vinculo.desativado_por_id = user.id
        await self.db.flush()

        await self.audit.log(
            usuario_id=user.id,
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
