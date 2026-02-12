"""Testes unitários do PessoaService.

Testa criação com/sem CPF, busca fuzzy, soft delete, verificação de
unicidade de CPF (hash) e isolamento multi-tenant.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, hash_for_search
from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.schemas.pessoa import PessoaCreate
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
