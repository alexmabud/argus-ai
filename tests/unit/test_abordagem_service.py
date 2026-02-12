"""Testes unitários do AbordagemService.

Testa criação de abordagem com vinculações, deduplicação por client_id,
materialização de relacionamentos e fluxo completo de criação em campo.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo
from app.schemas.abordagem import AbordagemCreate, AbordagemUpdate
from app.services.abordagem_service import AbordagemService


class TestCriarAbordagem:
    """Testes de criação de abordagem."""

    async def test_criar_abordagem_basica(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa criação de abordagem simples sem vinculações.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            latitude=-22.9068,
            longitude=-43.1729,
            endereco_texto="Rua Teste, 100",
        )
        abordagem = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert abordagem.id is not None
        assert abordagem.endereco_texto == "Rua Teste, 100"
        assert abordagem.guarnicao_id == guarnicao.id

    async def test_criar_abordagem_com_pessoas(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
        pessoa: Pessoa,
    ):
        """Testa criação de abordagem com pessoa vinculada.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
            pessoa: Fixture de pessoa.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Teste, 200",
            pessoa_ids=[pessoa.id],
        )
        abordagem = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(abordagem.pessoas) == 1
        assert abordagem.pessoas[0].pessoa_id == pessoa.id

    async def test_criar_abordagem_com_veiculo(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
        veiculo: Veiculo,
    ):
        """Testa criação de abordagem com veículo vinculado.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
            veiculo: Fixture de veículo.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Teste, 300",
            veiculo_ids=[veiculo.id],
        )
        abordagem = await service.criar(
            data=data,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(abordagem.veiculos) == 1
        assert abordagem.veiculos[0].veiculo_id == veiculo.id


class TestDeduplicacao:
    """Testes de deduplicação por client_id."""

    async def test_client_id_duplicado_retorna_existente(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que client_id duplicado retorna abordagem existente.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Offline, 100",
            client_id="offline-abc-123",
        )
        primeira = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        segunda = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        assert primeira.id == segunda.id


class TestAtualizarAbordagem:
    """Testes de atualização de abordagem."""

    async def test_atualizar_observacao(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa atualização parcial de observação.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Update, 100",
        )
        abordagem = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        update = AbordagemUpdate(observacao="Nova observação")
        atualizada = await service.atualizar(abordagem.id, update, usuario.id, guarnicao.id)
        assert atualizada.observacao == "Nova observação"

    async def test_buscar_por_id_inexistente(self, db_session: AsyncSession, guarnicao: Guarnicao):
        """Testa busca de abordagem inexistente retorna NaoEncontradoError.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
        """
        service = AbordagemService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.buscar_por_id(99999, guarnicao.id)
