"""Testes unitários do RelacionamentoService.

Testa materialização de vínculos com UPSERT, incremento de
frequência, ordenação (pessoa_id_a < pessoa_id_b) e busca
bidirecional de vínculos.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.services.relacionamento_service import RelacionamentoService


class TestRegistrarVinculo:
    """Testes de materialização de vínculos entre pessoas."""

    async def test_registrar_vinculo_duas_pessoas(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa criação de vínculo entre duas pessoas abordadas juntas.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        # Criar duas pessoas
        p1 = Pessoa(nome="Pessoa A", guarnicao_id=guarnicao.id)
        p2 = Pessoa(nome="Pessoa B", guarnicao_id=guarnicao.id)
        db_session.add_all([p1, p2])
        await db_session.flush()

        # Criar abordagem para referência
        abordagem = Abordagem(
            data_hora=datetime.now(UTC),
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(abordagem)
        await db_session.flush()

        service = RelacionamentoService(db_session)
        await service.registrar_vinculo([p1.id, p2.id], abordagem.id, abordagem.data_hora)

        vinculos = await service.buscar_vinculos(p1.id)
        assert len(vinculos) == 1
        assert vinculos[0].frequencia == 1

    async def test_upsert_incrementa_frequencia(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que UPSERT incrementa frequência quando par já existe.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        p1 = Pessoa(nome="Pessoa C", guarnicao_id=guarnicao.id)
        p2 = Pessoa(nome="Pessoa D", guarnicao_id=guarnicao.id)
        db_session.add_all([p1, p2])
        await db_session.flush()

        a1 = Abordagem(
            data_hora=datetime.now(UTC),
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        a2 = Abordagem(
            data_hora=datetime.now(UTC),
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add_all([a1, a2])
        await db_session.flush()

        service = RelacionamentoService(db_session)
        await service.registrar_vinculo([p1.id, p2.id], a1.id, a1.data_hora)
        await service.registrar_vinculo([p1.id, p2.id], a2.id, a2.data_hora)

        vinculos = await service.buscar_vinculos(p1.id)
        assert len(vinculos) == 1
        assert vinculos[0].frequencia == 2

    async def test_tres_pessoas_gera_tres_pares(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que 3 pessoas geram C(3,2)=3 pares de vínculos.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        p1 = Pessoa(nome="Pessoa E", guarnicao_id=guarnicao.id)
        p2 = Pessoa(nome="Pessoa F", guarnicao_id=guarnicao.id)
        p3 = Pessoa(nome="Pessoa G", guarnicao_id=guarnicao.id)
        db_session.add_all([p1, p2, p3])
        await db_session.flush()

        abordagem = Abordagem(
            data_hora=datetime.now(UTC),
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(abordagem)
        await db_session.flush()

        service = RelacionamentoService(db_session)
        await service.registrar_vinculo([p1.id, p2.id, p3.id], abordagem.id, abordagem.data_hora)

        # Cada pessoa deve ter 2 vínculos
        v1 = await service.buscar_vinculos(p1.id)
        v2 = await service.buscar_vinculos(p2.id)
        v3 = await service.buscar_vinculos(p3.id)
        assert len(v1) == 2
        assert len(v2) == 2
        assert len(v3) == 2


class TestBuscarVinculos:
    """Testes de busca bidirecional de vínculos."""

    async def test_buscar_bidirecional(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que vínculos são encontrados nas duas direções (A→B e B→A).

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        p1 = Pessoa(nome="Pessoa H", guarnicao_id=guarnicao.id)
        p2 = Pessoa(nome="Pessoa I", guarnicao_id=guarnicao.id)
        db_session.add_all([p1, p2])
        await db_session.flush()

        abordagem = Abordagem(
            data_hora=datetime.now(UTC),
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(abordagem)
        await db_session.flush()

        service = RelacionamentoService(db_session)
        await service.registrar_vinculo([p1.id, p2.id], abordagem.id, abordagem.data_hora)

        # Ambas direções devem retornar o mesmo vínculo
        vinculos_p1 = await service.buscar_vinculos(p1.id)
        vinculos_p2 = await service.buscar_vinculos(p2.id)
        assert len(vinculos_p1) == 1
        assert len(vinculos_p2) == 1
