"""Testes unitários para métodos de vínculo manual em PessoaService.

Verifica criação, listagem e remoção de vínculos manuais com
isolamento multi-tenant e auditoria.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.vinculo_manual import VinculoManual
from app.schemas.vinculo_manual import VinculoManualCreate
from app.services.pessoa_service import PessoaService


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
    p.nome = f"Pessoa {id}"
    p.foto_principal_url = None
    return p


@pytest.fixture
def db():
    """Fixture de sessão de banco mock."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    # begin_nested deve retornar um async context manager (não uma coroutine)
    session.begin_nested = MagicMock(return_value=AsyncMock())
    return session


@pytest.fixture
def service(db):
    """Fixture de PessoaService com db mock.

    Args:
        db: Sessão mock do banco.

    Returns:
        PessoaService com repositório e audit mockados.
    """
    svc = PessoaService(db)
    svc.repo = AsyncMock()
    svc.audit = AsyncMock()
    return svc


class TestCriarVinculoManual:
    """Testes para PessoaService.criar_vinculo_manual."""

    async def test_cria_vinculo_com_sucesso(self, service):
        """Testa criação de vínculo manual retorna VinculoManual.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada = make_pessoa(id=2, guarnicao_id=1)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada])

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão", descricao="Mora junto")
        result = await service.criar_vinculo_manual(1, data, user)

        assert isinstance(result, VinculoManual)
        assert result.pessoa_id == 1
        assert result.pessoa_vinculada_id == 2
        assert result.tipo == "Irmão"
        assert result.descricao == "Mora junto"
        service.audit.log.assert_awaited_once()

    async def test_pessoa_nao_encontrada_levanta_erro(self, service):
        """Testa que NaoEncontradoError é levantado se pessoa não existe.

        Args:
            service: PessoaService com mocks.
        """
        service.repo.get = AsyncMock(return_value=None)
        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão")

        with pytest.raises(NaoEncontradoError):
            await service.criar_vinculo_manual(999, data, make_user())

    async def test_vinculada_outra_guarnicao_levanta_acesso_negado(self, service):
        """Testa que AcessoNegadoError é levantado se vinculada é de outra guarnição.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada_outra = make_pessoa(id=2, guarnicao_id=99)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada_outra])

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Sócio")

        with pytest.raises(AcessoNegadoError):
            await service.criar_vinculo_manual(1, data, user)

    async def test_vinculo_duplicado_levanta_conflito(self, service):
        """Testa que ConflitoDadosError é levantado em duplicata.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada = make_pessoa(id=2, guarnicao_id=1)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada])
        service.db.flush = AsyncMock(side_effect=IntegrityError(None, None, None))
        service.db.rollback = AsyncMock()

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão")

        with pytest.raises(ConflitoDadosError):
            await service.criar_vinculo_manual(1, data, user)


class TestListarVinculosManuais:
    """Testes para PessoaService.listar_vinculos_manuais."""

    async def test_lista_vinculo_criado_por_outra_guarnicao(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        bpm,
        usuario: Usuario,
    ):
        """Vínculo criado por guarnição A deve aparecer para usuário de guarnição B.

        A ficha da pessoa é global — vínculos manuais devem ser visíveis
        independente de qual guarnição os registrou.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Guarnição A (do usuário que registrou o vínculo).
            bpm: BPM para criar a guarnição B.
            usuario: Usuário da guarnição A.
        """
        pessoa_a = Pessoa(nome="Abordado A", guarnicao_id=guarnicao.id)
        pessoa_b = Pessoa(nome="Abordado B", guarnicao_id=guarnicao.id)
        db_session.add_all([pessoa_a, pessoa_b])
        await db_session.flush()

        vinculo = VinculoManual(
            pessoa_id=pessoa_a.id,
            pessoa_vinculada_id=pessoa_b.id,
            tipo="Irmão",
            guarnicao_id=guarnicao.id,
        )
        db_session.add(vinculo)
        await db_session.flush()

        guarnicao_b = Guarnicao(nome="Cia B", bpm_id=bpm.id, codigo="CIA-B-VNL")
        db_session.add(guarnicao_b)
        await db_session.flush()

        user_b = Usuario(
            nome="Agente B",
            matricula="AGT-B-VNL",
            senha_hash="x",
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        service = PessoaService(db_session)
        resultado = await service.listar_vinculos_manuais(pessoa_a.id, user_b)

        assert len(resultado) == 1, "Vínculo deve aparecer independente da guarnição do usuário"
        assert resultado[0].tipo == "Irmão"


class TestRemoverVinculoManual:
    """Testes para PessoaService.remover_vinculo_manual."""

    async def test_remove_vinculo_com_soft_delete(self, service):
        """Testa que remoção executa soft delete corretamente.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        vinculo = MagicMock(spec=VinculoManual)
        vinculo.id = 5
        vinculo.ativo = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = vinculo
        service.db.execute = AsyncMock(return_value=mock_result)

        await service.remover_vinculo_manual(5, 1, user)

        assert vinculo.ativo is False
        assert vinculo.desativado_por_id == user.id
        assert vinculo.desativado_em is not None
        service.audit.log.assert_awaited_once()

    async def test_vinculo_nao_encontrado_levanta_erro(self, service):
        """Testa que NaoEncontradoError é levantado se vínculo não existe.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(NaoEncontradoError):
            await service.remover_vinculo_manual(999, 1, user)
