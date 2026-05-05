"""Testes unitários do PessoaService.

Testa criação com/sem CPF, busca fuzzy, soft delete, verificação de
unicidade de CPF (hash) e visibilidade global de pessoas (sem filtro de guarnição).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, hash_for_search
from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.security import hash_senha
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.schemas.pessoa import EnderecoCreate, PessoaCreate
from app.services.pessoa_service import PessoaService


class TestCriarPessoa:
    """Testes de criação de pessoa."""

    async def test_criar_pessoa_sem_cpf(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa criação de pessoa sem CPF.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="Maria da Silva", apelido="Marinha")
        pessoa = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert pessoa.id is not None
        assert pessoa.nome == "Maria da Silva"
        assert pessoa.apelido == "Marinha"
        assert pessoa.cpf_encrypted is None
        assert pessoa.cpf_hash is None

    async def test_criar_pessoa_com_cpf(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa criação de pessoa com CPF criptografado.

        Verifica que o CPF é criptografado (Fernet) e o hash gerado
        para busca (SHA-256).

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="João Santos", cpf="123.456.789-00")
        pessoa = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert pessoa.cpf_encrypted is not None
        assert pessoa.cpf_hash is not None
        assert pessoa.cpf_hash == hash_for_search("123.456.789-00")
        assert decrypt(pessoa.cpf_encrypted) == "123.456.789-00"

    async def test_criar_pessoa_cpf_duplicado(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa rejeição de CPF duplicado na mesma guarnição.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data1 = PessoaCreate(nome="Pessoa A", cpf="111.111.111-11")
        await service.criar(data=data1, user_id=usuario.id, guarnicao_id=guarnicao.id)

        data2 = PessoaCreate(nome="Pessoa B", cpf="111.111.111-11")
        with pytest.raises(ConflitoDadosError):
            await service.criar(data=data2, user_id=usuario.id, guarnicao_id=guarnicao.id)

    async def test_criar_pessoa_propaga_nome_mae(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que nome_mae do DTO é propagado para o objeto Pessoa criado.

        Garante que o PessoaService.criar persiste o campo nome_mae quando
        informado no PessoaCreate, evitando regressão silenciosa.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="Fulano de Tal", nome_mae="Maria das Dores")
        pessoa = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert pessoa.nome_mae == "Maria das Dores"


class TestBuscarPessoa:
    """Testes de busca de pessoa."""

    async def test_buscar_por_id(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa busca de pessoa por ID com verificação de tenant.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="Teste Busca")
        pessoa = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        encontrada = await service.buscar_por_id(pessoa.id, usuario)
        assert encontrada.id == pessoa.id
        assert encontrada.nome == "Teste Busca"

    async def test_buscar_por_id_inexistente(self, db_session: AsyncSession, usuario: Usuario):
        """Testa busca de pessoa inexistente retorna NaoEncontradoError.

        Args:
            db_session: Sessão do banco de testes.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.buscar_por_id(99999, usuario)

    async def test_buscar_por_id_retorna_pessoa_sem_guarnicao(
        self, db_session: AsyncSession, usuario: Usuario
    ):
        """Pessoa sem guarnicao_id deve ser visível por qualquer usuário.

        Pessoas são cadastros globais — não devem ser bloqueadas pelo
        TenantFilter mesmo quando guarnicao_id é NULL.

        Args:
            db_session: Sessão do banco de testes.
            usuario: Usuário com guarnicao_id definido.
        """
        pessoa = Pessoa(nome="Cadastro Global", guarnicao_id=None)
        db_session.add(pessoa)
        await db_session.flush()

        service = PessoaService(db_session)
        encontrada = await service.buscar_por_id(pessoa.id, usuario)
        assert encontrada.id == pessoa.id

    async def test_buscar_por_nome_retorna_pessoa_de_outra_guarnicao(
        self, db_session: AsyncSession, usuario: Usuario, bpm: Bpm
    ):
        """Busca por nome deve retornar pessoas de qualquer guarnição.

        O isolamento de guarnição não se aplica a pessoas — apenas a abordagens.
        Um usuário deve encontrar qualquer pessoa cadastrada no sistema.

        Args:
            db_session: Sessão do banco de testes.
            usuario: Usuário da guarnição A.
            bpm: BPM compartilhado para criar a guarnição B.
        """
        guarnicao_b = Guarnicao(nome="Outra Cia", bpm_id=bpm.id, codigo="OUTRA-001")
        db_session.add(guarnicao_b)
        await db_session.flush()

        pessoa_outra = Pessoa(nome="Fulano de Outra Guarnicao", guarnicao_id=guarnicao_b.id)
        db_session.add(pessoa_outra)
        await db_session.flush()

        service = PessoaService(db_session)
        resultados = await service.buscar(nome="Fulano de Outra", user=usuario)
        ids = [p.id for p in resultados]
        assert pessoa_outra.id in ids, "Pessoa de outra guarnição deve aparecer na busca"


class TestDesativarPessoa:
    """Testes de soft delete de pessoa."""

    async def test_soft_delete(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa soft delete marca pessoa como inativa.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="Para Desativar")
        pessoa = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        assert pessoa.ativo is True

        desativada = await service.desativar(pessoa.id, usuario)
        assert desativada.ativo is False
        assert desativada.desativado_em is not None


class TestAdminPermissoes:
    """Testes de permissões de administrador para edição de dados de pessoas."""

    async def test_admin_adiciona_endereco_em_pessoa_de_outra_guarnicao(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        bpm: Bpm,
    ):
        """Admin deve poder adicionar endereço a pessoa de qualquer guarnição.

        Usuários com is_admin=True não devem ser bloqueados pelo TenantFilter
        ao editar dados cadastrais de pessoas de outras guarnições.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Guarnição A (da pessoa).
            bpm: BPM para criar a guarnição B (do admin).
        """
        guarnicao_b = Guarnicao(nome="Cia Admin", bpm_id=bpm.id, codigo="ADM-001")
        db_session.add(guarnicao_b)
        await db_session.flush()

        admin = Usuario(
            nome="Administrador",
            matricula="ADM-TST-01",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao_b.id,
            is_admin=True,
        )
        db_session.add(admin)
        await db_session.flush()

        pessoa = Pessoa(nome="Abordado Alvo", guarnicao_id=guarnicao.id)
        db_session.add(pessoa)
        await db_session.flush()

        service = PessoaService(db_session)
        data = EnderecoCreate(endereco="Rua dos Testes, 1", cidade="Brasília", estado="DF")
        endereco = await service.adicionar_endereco(pessoa.id, data, admin)

        assert endereco.id is not None
        assert endereco.pessoa_id == pessoa.id

    async def test_admin_edita_dados_de_pessoa_sem_guarnicao(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        bpm: Bpm,
    ):
        """Admin deve poder editar pessoa com guarnicao_id=None.

        Pessoas migradas sem guarnicao ficavam inacessíveis para edição.
        Admins devem poder atualizar qualquer pessoa independente de guarnicao_id.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Guarnição do admin.
            bpm: BPM (apenas para consistência de fixtures).
        """
        admin = Usuario(
            nome="Admin Global",
            matricula="ADM-TST-02",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao.id,
            is_admin=True,
        )
        db_session.add(admin)
        await db_session.flush()

        pessoa = Pessoa(nome="Pessoa Migrada", guarnicao_id=None)
        db_session.add(pessoa)
        await db_session.flush()

        service = PessoaService(db_session)
        data = EnderecoCreate(endereco="Setor Comercial Sul, 10", cidade="Brasília", estado="DF")
        endereco = await service.adicionar_endereco(pessoa.id, data, admin)

        assert endereco.id is not None


class TestMaskCpf:
    """Testes da mascaração de CPF."""

    async def test_mask_cpf_com_cpf(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa mascaração de CPF retorna formato LGPD (***.***.***-XX).

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = PessoaService(db_session)
        data = PessoaCreate(nome="Teste CPF", cpf="123.456.789-00")
        pessoa = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        masked = PessoaService.mask_cpf(pessoa)
        assert masked is not None
        assert masked.startswith("*")
        assert masked.endswith("00")

    async def test_mask_cpf_sem_cpf(self, db_session: AsyncSession, pessoa: Pessoa):
        """Testa mascaração retorna None quando pessoa não tem CPF.

        Args:
            db_session: Sessão do banco de testes.
            pessoa: Fixture de pessoa sem CPF.
        """
        masked = PessoaService.mask_cpf(pessoa)
        assert masked is None
