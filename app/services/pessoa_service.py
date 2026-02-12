"""Serviço de lógica de negócio para Pessoa.

Gerencia criação, atualização, busca e soft delete de pessoas,
com criptografia CPF (Fernet), busca fuzzy (pg_trgm) e auditoria.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt, hash_for_search
from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.permissions import TenantFilter
from app.models.endereco import EnderecoPessoa
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.repositories.pessoa_repo import PessoaRepository
from app.schemas.pessoa import EnderecoCreate, PessoaCreate, PessoaUpdate
from app.services.audit_service import AuditService


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
            detalhes={"nome": data.nome},
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
        if cpf:
            cpf_hash = hash_for_search(cpf)
            result = await self.repo.get_by_cpf_hash(cpf_hash, user.guarnicao_id)
            return [result] if result else []

        if nome:
            return list(
                await self.repo.search_by_nome_fuzzy(
                    nome, user.guarnicao_id, skip=skip, limit=limit
                )
            )

        return list(await self.repo.get_all(skip=skip, limit=limit, guarnicao_id=user.guarnicao_id))

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
            localizacao=localizacao,
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
        )
        self.db.add(endereco)
        await self.db.flush()
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
            return None
