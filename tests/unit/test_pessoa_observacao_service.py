"""Testes unitários para PessoaObservacaoService.

Verifica criação, listagem, atualização e soft delete de observações
com isolamento multi-tenant e auditoria.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AcessoNegadoError, NaoEncontradoError
from app.models.pessoa import Pessoa
from app.models.pessoa_observacao import PessoaObservacao
from app.models.usuario import Usuario
from app.schemas.pessoa_observacao import PessoaObservacaoCreate, PessoaObservacaoUpdate
from app.services.pessoa_observacao_service import PessoaObservacaoService


def make_user(guarnicao_id: int = 1) -> Usuario:
    """Cria usuário mock para testes.

    Args:
        guarnicao_id: ID da guarnição do usuário.

    Returns:
        Usuário mock com id e guarnicao_id.
    """
    u = MagicMock(spec=Usuario)
    u.id = 10
    u.guarnicao_id = guarnicao_id
    return u


def make_pessoa(id: int, guarnicao_id: int = 1) -> Pessoa:
    """Cria pessoa mock para testes.

    Args:
        id: ID da pessoa.
        guarnicao_id: ID da guarnição da pessoa.

    Returns:
        Pessoa mock com id, guarnicao_id e ativo=True.
    """
    p = MagicMock(spec=Pessoa)
    p.id = id
    p.guarnicao_id = guarnicao_id
    p.ativo = True
    return p


def make_obs(id: int, pessoa_id: int, guarnicao_id: int = 1) -> PessoaObservacao:
    """Cria observação mock para testes.

    Args:
        id: ID da observação.
        pessoa_id: ID da pessoa dona da observação.
        guarnicao_id: ID da guarnição da observação.

    Returns:
        PessoaObservacao mock com id, pessoa_id, guarnicao_id e ativo=True.
    """
    obs = MagicMock(spec=PessoaObservacao)
    obs.id = id
    obs.pessoa_id = pessoa_id
    obs.guarnicao_id = guarnicao_id
    obs.ativo = True
    obs.texto = "Observação de teste"
    return obs


@pytest.fixture
def db():
    """Fixture de sessão de banco mock."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(db):
    """Fixture de PessoaObservacaoService com db mock.

    Args:
        db: Sessão mock do banco.

    Returns:
        PessoaObservacaoService com repositórios e audit mockados.
    """
    svc = PessoaObservacaoService(db)
    svc.pessoa_repo = AsyncMock()
    svc.obs_repo = AsyncMock()
    svc.audit = AsyncMock()
    return svc


class TestCriarObservacao:
    """Testes para PessoaObservacaoService.criar."""

    async def test_cria_com_sucesso(self, service):
        """Testa criação de observação retorna PessoaObservacao.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        service.pessoa_repo.get = AsyncMock(return_value=pessoa)
        service.obs_repo.create = AsyncMock(side_effect=lambda obs: obs)

        data = PessoaObservacaoCreate(texto="Possui tatuagem no braço direito")
        result = await service.criar(pessoa_id=1, data=data, user=user)

        assert isinstance(result, PessoaObservacao)
        assert result.pessoa_id == 1
        assert result.texto == "Possui tatuagem no braço direito"
        assert result.guarnicao_id == 1
        service.audit.log.assert_awaited_once()

    async def test_pessoa_inexistente(self, service):
        """Testa que NaoEncontradoError é levantado se pessoa não existe.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        service.pessoa_repo.get = AsyncMock(return_value=None)
        data = PessoaObservacaoCreate(texto="Observação qualquer")

        with pytest.raises(NaoEncontradoError):
            await service.criar(pessoa_id=999, data=data, user=make_user())

    async def test_pessoa_outra_guarnicao(self, service):
        """Testa que AcessoNegadoError é levantado se pessoa é de outra guarnição.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=99)
        service.pessoa_repo.get = AsyncMock(return_value=pessoa)
        data = PessoaObservacaoCreate(texto="Observação qualquer")

        with pytest.raises(AcessoNegadoError):
            await service.criar(pessoa_id=1, data=data, user=user)


class TestListarObservacoes:
    """Testes para PessoaObservacaoService.listar."""

    async def test_lista_com_sucesso(self, service, db):
        """Testa listagem retorna observações ativas da pessoa.

        Args:
            service: PessoaObservacaoService com mocks.
            db: Sessão mock do banco.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        obs1 = make_obs(id=1, pessoa_id=1)
        obs2 = make_obs(id=2, pessoa_id=1)
        service.pessoa_repo.get = AsyncMock(return_value=pessoa)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [obs2, obs1]
        db.execute = AsyncMock(return_value=mock_result)

        result = await service.listar(pessoa_id=1, user=user)

        assert len(result) == 2
        assert result[0].id == 2
        assert result[1].id == 1

    async def test_pessoa_inexistente_na_listagem(self, service):
        """Testa que NaoEncontradoError é levantado ao listar de pessoa inexistente.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        service.pessoa_repo.get = AsyncMock(return_value=None)

        with pytest.raises(NaoEncontradoError):
            await service.listar(pessoa_id=999, user=make_user())


class TestAtualizarObservacao:
    """Testes para PessoaObservacaoService.atualizar."""

    async def test_atualiza_com_sucesso(self, service):
        """Testa atualização de texto de observação existente.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        obs = make_obs(id=5, pessoa_id=1, guarnicao_id=1)
        service.obs_repo.get = AsyncMock(return_value=obs)
        service.obs_repo.update = AsyncMock(side_effect=lambda o, d: o)

        data = PessoaObservacaoUpdate(texto="Texto atualizado")
        result = await service.atualizar(obs_id=5, pessoa_id=1, data=data, user=user)

        assert result is obs
        service.obs_repo.update.assert_awaited_once_with(obs, {"texto": "Texto atualizado"})
        service.audit.log.assert_awaited_once()

    async def test_obs_inexistente(self, service):
        """Testa que NaoEncontradoError é levantado se observação não existe.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        service.obs_repo.get = AsyncMock(return_value=None)
        data = PessoaObservacaoUpdate(texto="Texto qualquer")

        with pytest.raises(NaoEncontradoError):
            await service.atualizar(obs_id=999, pessoa_id=1, data=data, user=make_user())

    async def test_obs_outra_guarnicao(self, service):
        """Testa que AcessoNegadoError é levantado se observação é de outra guarnição.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        obs = make_obs(id=5, pessoa_id=1, guarnicao_id=99)
        service.obs_repo.get = AsyncMock(return_value=obs)
        data = PessoaObservacaoUpdate(texto="Texto qualquer")

        with pytest.raises(AcessoNegadoError):
            await service.atualizar(obs_id=5, pessoa_id=1, data=data, user=user)

    async def test_obs_de_outra_pessoa(self, service):
        """Testa que NaoEncontradoError é levantado se obs não pertence à pessoa.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        obs = make_obs(id=5, pessoa_id=2, guarnicao_id=1)  # pessoa_id=2, mas esperamos 1
        service.obs_repo.get = AsyncMock(return_value=obs)
        data = PessoaObservacaoUpdate(texto="Texto qualquer")

        with pytest.raises(NaoEncontradoError):
            await service.atualizar(obs_id=5, pessoa_id=1, data=data, user=user)


class TestDeletarObservacao:
    """Testes para PessoaObservacaoService.deletar."""

    async def test_deleta_com_soft_delete(self, service):
        """Testa que remoção executa soft delete e registra auditoria.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        user = make_user(guarnicao_id=1)
        obs = make_obs(id=5, pessoa_id=1, guarnicao_id=1)
        service.obs_repo.get = AsyncMock(return_value=obs)
        service.obs_repo.soft_delete = AsyncMock(return_value=obs)

        await service.deletar(obs_id=5, pessoa_id=1, user=user)

        service.obs_repo.soft_delete.assert_awaited_once_with(obs, deleted_by_id=user.id)
        service.audit.log.assert_awaited_once()

    async def test_obs_inexistente_ao_deletar(self, service):
        """Testa que NaoEncontradoError é levantado ao deletar observação inexistente.

        Args:
            service: PessoaObservacaoService com mocks.
        """
        service.obs_repo.get = AsyncMock(return_value=None)

        with pytest.raises(NaoEncontradoError):
            await service.deletar(obs_id=999, pessoa_id=1, user=make_user())
