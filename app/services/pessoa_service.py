"""Serviço de lógica de negócio para Pessoa.

Gerencia criação, atualização, busca e soft delete de pessoas,
com criptografia CPF (Fernet), busca fuzzy (pg_trgm) e auditoria.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt, hash_for_search
from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.core.permissions import TenantFilter
from app.models.endereco import EnderecoPessoa
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.vinculo_manual import VinculoManual
from app.repositories.pessoa_repo import PessoaRepository
from app.schemas.pessoa import EnderecoCreate, EnderecoUpdate, PessoaCreate, PessoaUpdate
from app.schemas.vinculo_manual import VinculoManualCreate
from app.services.audit_service import AuditService

logger = logging.getLogger("argus")


class PessoaService:
    """Serviço de Pessoa com criptografia CPF e busca fuzzy.

    Implementa lógica de negócio para gerenciamento de pessoas abordadas,
    incluindo criptografia de CPF com Fernet (AES-256), busca fuzzy via
    pg_trgm, verificação de unicidade por hash SHA-256 e auditoria de
    todas as mutações. NÃO importa ou depende de FastAPI.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Pessoa com busca fuzzy e CPF hash.
        audit: Serviço de auditoria para registro de ações.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de Pessoa.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = PessoaRepository(db)
        self.audit = AuditService(db)

    async def criar(
        self,
        data: PessoaCreate,
        user_id: int,
        guarnicao_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Pessoa:
        """Cria nova pessoa com CPF criptografado.

        Se CPF informado, criptografa com Fernet (AES-256) e gera hash
        SHA-256 para busca. Verifica unicidade do CPF por hash dentro
        da mesma guarnição antes de criar.

        Args:
            data: Dados de criação da pessoa (nome, cpf, nascimento, etc).
            user_id: ID do usuário que está criando o registro.
            guarnicao_id: ID da guarnição para isolamento multi-tenant.
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Pessoa criada com ID atribuído pelo banco.

        Raises:
            ConflitoDadosError: Se CPF já cadastrado na mesma guarnição.
        """
        cpf_encrypted = None
        cpf_hash = None
        if data.cpf:
            cpf_hash = hash_for_search(data.cpf)
            existing = await self.repo.get_by_cpf_hash(cpf_hash, guarnicao_id)
            if existing:
                raise ConflitoDadosError("Pessoa com este CPF já cadastrada")
            cpf_encrypted = encrypt(data.cpf)

        pessoa = Pessoa(
            nome=data.nome,
            cpf_encrypted=cpf_encrypted,
            cpf_hash=cpf_hash,
            data_nascimento=data.data_nascimento,
            apelido=data.apelido,
            observacoes=data.observacoes,
            guarnicao_id=guarnicao_id,
        )

        await self.repo.create(pessoa)

        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="pessoa",
            recurso_id=pessoa.id,
            detalhes={"acao": "cadastro_pessoa"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return pessoa

    async def atualizar(
        self,
        pessoa_id: int,
        data: PessoaUpdate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Pessoa:
        """Atualiza pessoa existente com verificação de tenant.

        Re-criptografa CPF se alterado. Verifica unicidade do novo CPF
        antes de atualizar. Registra campos alterados na auditoria.

        Args:
            pessoa_id: ID da pessoa a atualizar.
            data: Dados de atualização parcial (apenas campos enviados).
            user: Usuário autenticado (para verificação de tenant).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Pessoa atualizada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
            ConflitoDadosError: Se novo CPF já cadastrado por outra pessoa.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        update_data = data.model_dump(exclude_unset=True)

        if "cpf" in update_data:
            cpf_value = update_data.pop("cpf")
            if cpf_value:
                new_hash = hash_for_search(cpf_value)
                existing = await self.repo.get_by_cpf_hash(new_hash, user.guarnicao_id)
                if existing and existing.id != pessoa_id:
                    raise ConflitoDadosError("Pessoa com este CPF já cadastrada")
                update_data["cpf_encrypted"] = encrypt(cpf_value)
                update_data["cpf_hash"] = new_hash
            else:
                update_data["cpf_encrypted"] = None
                update_data["cpf_hash"] = None

        await self.repo.update(pessoa, update_data)

        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="pessoa",
            recurso_id=pessoa.id,
            detalhes={"campos_alterados": list(update_data.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return pessoa

    async def buscar_por_id(self, pessoa_id: int, user: Usuario) -> Pessoa:
        """Obtém pessoa por ID com verificação de tenant.

        Args:
            pessoa_id: ID da pessoa a buscar.
            user: Usuário autenticado (para verificação de guarnição).

        Returns:
            Pessoa encontrada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)
        return pessoa

    async def buscar_detalhe(self, pessoa_id: int, user: Usuario) -> Pessoa:
        """Obtém pessoa com todos os relacionamentos carregados (eager load).

        Carrega endereços, fotos e relacionamentos em uma única query
        para evitar N+1 queries na view de detalhe.

        Args:
            pessoa_id: ID da pessoa a buscar.
            user: Usuário autenticado (para filtro de guarnição).

        Returns:
            Pessoa com relacionamentos carregados.

        Raises:
            NaoEncontradoError: Se pessoa não existe na guarnição.
        """
        pessoa = await self.repo.get_detail(pessoa_id, user.guarnicao_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        return pessoa

    async def buscar(
        self,
        nome: str | None = None,
        cpf: str | None = None,
        apelido: str | None = None,
        skip: int = 0,
        limit: int = 20,
        user: Usuario | None = None,
    ) -> list:
        """Busca pessoas por nome (fuzzy), CPF (hash) ou lista paginada.

        Despacha para o método de busca apropriado conforme os filtros:
        - CPF informado: busca exata por hash SHA-256.
        - Nome informado: busca fuzzy via pg_trgm (similarity).
        - Sem filtros: lista paginada da guarnição.

        Args:
            nome: Termo de busca por nome (fuzzy, opcional).
            cpf: CPF para busca exata via hash (opcional).
            apelido: Reservado para busca futura por apelido (opcional).
            skip: Número de registros a pular (paginação).
            limit: Número máximo de resultados.
            user: Usuário autenticado (para filtro multi-tenant).

        Returns:
            Lista de pessoas encontradas.
        """
        guarnicao_id = user.guarnicao_id if user else None
        if cpf:
            cpf_hash = hash_for_search(cpf)
            result = await self.repo.get_by_cpf_hash(cpf_hash, guarnicao_id)
            return [result] if result else []

        if nome:
            return list(
                await self.repo.search_by_nome_fuzzy(nome, guarnicao_id, skip=skip, limit=limit)
            )

        return list(await self.repo.get_all(skip=skip, limit=limit, guarnicao_id=guarnicao_id))

    async def desativar(
        self,
        pessoa_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Pessoa:
        """Soft delete de pessoa com auditoria.

        Marca pessoa como inativa (ativo=False) sem remoção física.
        Registra data, usuário responsável e evento de auditoria.

        Args:
            pessoa_id: ID da pessoa a desativar.
            user: Usuário autenticado (para verificação de tenant e auditoria).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Pessoa desativada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        await self.repo.soft_delete(pessoa, deleted_by_id=user.id)

        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="pessoa",
            recurso_id=pessoa.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return pessoa

    async def adicionar_endereco(
        self,
        pessoa_id: int,
        data: EnderecoCreate,
        user: Usuario,
    ) -> EnderecoPessoa:
        """Adiciona endereço a pessoa com PostGIS se coordenadas informadas.

        Cria registro de endereço vinculado à pessoa. Se latitude e longitude
        forem informadas, gera ponto geográfico WKT para armazenamento
        PostGIS (SRID 4326).

        Args:
            pessoa_id: ID da pessoa para vincular o endereço.
            data: Dados do endereço (texto, coordenadas, datas).
            user: Usuário autenticado (para verificação de tenant).

        Returns:
            Endereço criado com ID atribuído.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        localizacao = None
        if data.latitude is not None and data.longitude is not None:
            localizacao = f"POINT({data.longitude} {data.latitude})"

        endereco = EnderecoPessoa(
            pessoa_id=pessoa_id,
            endereco=data.endereco,
            bairro=data.bairro,
            cidade=data.cidade,
            estado=data.estado,
            estado_id=data.estado_id,
            cidade_id=data.cidade_id,
            bairro_id=data.bairro_id,
            localizacao=localizacao,
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
        )
        self.db.add(endereco)
        await self.db.flush()
        return endereco

    async def atualizar_endereco(
        self,
        pessoa_id: int,
        endereco_id: int,
        data: EnderecoUpdate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EnderecoPessoa:
        """Atualiza endereço existente de uma pessoa.

        Se latitude e longitude forem informadas, atualiza o ponto PostGIS.
        Registra auditoria com campos alterados.

        Args:
            pessoa_id: ID da pessoa dona do endereço.
            endereco_id: ID do endereço a atualizar.
            data: Dados de atualização parcial.
            user: Usuário autenticado (para verificação de tenant).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Endereço atualizado.

        Raises:
            NaoEncontradoError: Se pessoa ou endereço não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        result = await self.db.execute(
            select(EnderecoPessoa).where(
                EnderecoPessoa.id == endereco_id,
                EnderecoPessoa.pessoa_id == pessoa_id,
                EnderecoPessoa.ativo == True,  # noqa: E712
            )
        )
        endereco = result.scalar_one_or_none()
        if not endereco:
            raise NaoEncontradoError("Endereço")

        update_data = data.model_dump(exclude_unset=True)

        # Atualizar geometria PostGIS se coordenadas mudaram
        lat = update_data.pop("latitude", None)
        lng = update_data.pop("longitude", None)
        if lat is not None and lng is not None:
            endereco.localizacao = f"POINT({lng} {lat})"

        for field, value in update_data.items():
            setattr(endereco, field, value)

        await self.db.flush()

        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="endereco",
            recurso_id=endereco.id,
            detalhes={"campos_alterados": list(data.model_dump(exclude_unset=True).keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return endereco

    @staticmethod
    def mask_cpf(pessoa: Pessoa) -> str | None:
        """Mascara CPF para exibição segura (***.***.***-XX).

        Descriptografa o CPF armazenado e retorna versão mascarada
        exibindo apenas os últimos 3 dígitos para conformidade LGPD.

        Args:
            pessoa: Instância de Pessoa com cpf_encrypted.

        Returns:
            CPF mascarado no formato "***.***.***-XX" ou None se
            pessoa não possui CPF cadastrado.
        """
        if not pessoa.cpf_encrypted:
            return None
        try:
            cpf = decrypt(pessoa.cpf_encrypted)
            clean = cpf.replace(".", "").replace("-", "")
            return f"***.***.*{clean[-3]}-{clean[-2:]}"
        except Exception:
            logger.warning("Falha ao descriptografar CPF da pessoa %s", pessoa.id)
            return None

    @staticmethod
    def decrypt_cpf(pessoa: Pessoa) -> str | None:
        """Descriptografa CPF completo para exibição no detalhe.

        Args:
            pessoa: Instância de Pessoa com cpf_encrypted.

        Returns:
            CPF formatado (XXX.XXX.XXX-XX) ou None se sem CPF.
        """
        if not pessoa.cpf_encrypted:
            return None
        try:
            cpf = decrypt(pessoa.cpf_encrypted)
            clean = cpf.replace(".", "").replace("-", "")
            if len(clean) == 11:
                return f"{clean[:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:]}"
            return cpf
        except Exception:
            logger.warning("Falha ao descriptografar CPF da pessoa %s", pessoa.id)
            return None

    async def criar_vinculo_manual(
        self,
        pessoa_id: int,
        data: VinculoManualCreate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> VinculoManual:
        """Cria vínculo manual entre duas pessoas com validação de tenant.

        Verifica que ambas as pessoas pertencem à mesma guarnição antes
        de criar. Captura IntegrityError do banco para duplicatas.
        Registra auditoria na criação.

        Args:
            pessoa_id: ID da pessoa dona do vínculo.
            data: Dados do vínculo (pessoa_vinculada_id, tipo, descricao).
            user: Usuário autenticado.
            ip_address: IP da requisição para auditoria.
            user_agent: User-Agent para auditoria.

        Returns:
            VinculoManual criado.

        Raises:
            NaoEncontradoError: Se pessoa ou pessoa vinculada não existem.
            AcessoNegadoError: Se pessoa não pertence à guarnição do user,
                ou se pessoa vinculada pertence a outra guarnição.
            ConflitoDadosError: Se vínculo já existe (UNIQUE constraint).
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        vinculada = await self.repo.get(data.pessoa_vinculada_id)
        if not vinculada:
            raise NaoEncontradoError("Pessoa vinculada")
        if vinculada.guarnicao_id != user.guarnicao_id:
            raise AcessoNegadoError("Pessoa vinculada pertence a outra guarnição")

        vinculo = VinculoManual(
            pessoa_id=pessoa_id,
            pessoa_vinculada_id=data.pessoa_vinculada_id,
            tipo=data.tipo,
            descricao=data.descricao,
            guarnicao_id=user.guarnicao_id,
        )
        self.db.add(vinculo)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflitoDadosError("Vínculo já cadastrado entre essas pessoas")

        # Criar registro inverso (bidirecional): Pedro→João além de João→Pedro
        try:
            async with self.db.begin_nested():
                vinculo_inverso = VinculoManual(
                    pessoa_id=data.pessoa_vinculada_id,
                    pessoa_vinculada_id=pessoa_id,
                    tipo=data.tipo,
                    descricao=data.descricao,
                    guarnicao_id=user.guarnicao_id,
                )
                self.db.add(vinculo_inverso)
                await self.db.flush()
        except IntegrityError:
            # Inverso já existia (dados anteriores ao fix) — ignorar silenciosamente
            pass

        # Carregar pessoa_vinculada explicitamente após flush para evitar
        # MissingGreenlet ao acessar o relacionamento no router em contexto async.
        await self.db.refresh(vinculo, attribute_names=["pessoa_vinculada"])

        await self.audit.log(
            usuario_id=user.id,
            acao="CREATE",
            recurso="vinculo_manual",
            recurso_id=vinculo.id,
            detalhes={
                "pessoa_id": pessoa_id,
                "pessoa_vinculada_id": data.pessoa_vinculada_id,
                "tipo": data.tipo,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return vinculo

    async def listar_vinculos_manuais(
        self,
        pessoa_id: int,
        user: Usuario,
    ) -> list[VinculoManual]:
        """Lista vínculos manuais ativos de uma pessoa.

        Filtra por pessoa_id e guarnicao_id do user, excluindo
        registros com soft delete (ativo=False).

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado (para filtro de guarnição).

        Returns:
            Lista de VinculoManual ativos da pessoa.
        """
        query = select(VinculoManual).where(
            VinculoManual.pessoa_id == pessoa_id,
            VinculoManual.guarnicao_id == user.guarnicao_id,
            VinculoManual.ativo == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def remover_vinculo_manual(
        self,
        vinculo_id: int,
        pessoa_id: int,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Remove vínculo manual com soft delete.

        Marca o vínculo como inativo sem remoção física. Verifica
        que o vínculo pertence à guarnição do usuário.

        Args:
            vinculo_id: ID do vínculo a remover.
            pessoa_id: ID da pessoa dona do vínculo (validação extra).
            user: Usuário autenticado.
            ip_address: IP da requisição para auditoria.
            user_agent: User-Agent para auditoria.

        Raises:
            NaoEncontradoError: Se vínculo não existe ou não pertence
                à guarnição do user.
        """
        query = select(VinculoManual).where(
            VinculoManual.id == vinculo_id,
            VinculoManual.pessoa_id == pessoa_id,
            VinculoManual.guarnicao_id == user.guarnicao_id,
            VinculoManual.ativo == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        vinculo = result.scalar_one_or_none()
        if not vinculo:
            raise NaoEncontradoError("Vínculo manual")

        vinculo.ativo = False
        vinculo.desativado_em = datetime.now(UTC)
        vinculo.desativado_por_id = user.id

        # Remover registro inverso (bidirecional)
        query_inverso = select(VinculoManual).where(
            VinculoManual.pessoa_id == vinculo.pessoa_vinculada_id,
            VinculoManual.pessoa_vinculada_id == pessoa_id,
            VinculoManual.guarnicao_id == user.guarnicao_id,
            VinculoManual.ativo == True,  # noqa: E712
        )
        result_inverso = await self.db.execute(query_inverso)
        vinculo_inverso = result_inverso.scalar_one_or_none()
        if vinculo_inverso:
            vinculo_inverso.ativo = False
            vinculo_inverso.desativado_em = datetime.now(UTC)
            vinculo_inverso.desativado_por_id = user.id

        await self.db.flush()

        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="vinculo_manual",
            recurso_id=vinculo_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
