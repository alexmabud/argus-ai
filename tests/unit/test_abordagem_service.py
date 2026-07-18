"""Testes unitários do AbordagemService.

Testa criação de abordagem com vinculações, deduplicação por client_id,
materialização de relacionamentos e fluxo completo de criação em campo.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.abordagem import Abordagem, AbordagemPessoa
from app.models.bpm import Bpm
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
        assert abordagem.endereco_texto == "RUA TESTE, 100"
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
        await db_session.refresh(abordagem, attribute_names=["pessoas"])
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
        await db_session.refresh(abordagem, attribute_names=["veiculos"])
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
        # observacao é normalizada para MAIÚSCULAS no schema
        atualizada = await service.atualizar(abordagem.id, update, usuario)
        assert atualizada.observacao == "NOVA OBSERVAÇÃO"

    async def test_buscar_por_id_inexistente(self, db_session: AsyncSession, guarnicao: Guarnicao):
        """Testa busca de abordagem inexistente retorna NaoEncontradoError.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
        """
        service = AbordagemService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.buscar_por_id(99999, guarnicao.id)


class TestVincularPessoa:
    """Testes de vincular_pessoa, incluindo o tratamento de corrida no insert."""

    async def test_vincular_pessoa_corrida_no_insert_gera_conflito_dados(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
        pessoa: Pessoa,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Corrida entre duas requisições vinculando a mesma pessoa pela 1a vez.

        Simula o cenário em que a checagem em memória (abordagem.pessoas)
        não reflete um vínculo já criado por outra requisição concorrente —
        o INSERT perdedor colide com a unique constraint uq_abordagem_pessoa,
        e o service deve converter isso em ConflitoDadosError, não deixar o
        IntegrityError vazar como erro 500. Mesmo padrão de
        test_pessoa_veiculo_service.py::test_vincular_corrida_no_insert_gera_conflito_dados.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário (dono da abordagem).
            pessoa: Fixture de pessoa a vincular.
            monkeypatch: Fixture do pytest para substituir buscar_detalhe.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(data_hora=datetime.now(UTC), endereco_texto="Rua Teste, 100")
        abordagem = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        await service.vincular_pessoa(abordagem.id, pessoa.id, usuario)

        # Objeto avulso (não gerenciado pela sessão) simulando uma leitura
        # desatualizada de abordagem.pessoas — evita mutar a coleção real
        # mapeada pelo SQLAlchemy, que dispararia cascade delete-orphan.
        abordagem_desatualizada = SimpleNamespace(
            id=abordagem.id, usuario_id=usuario.id, pessoas=[], data_hora=abordagem.data_hora
        )

        async def buscar_detalhe_desatualizado(*args, **kwargs):
            return abordagem_desatualizada

        monkeypatch.setattr(service, "buscar_detalhe", buscar_detalhe_desatualizado)

        with pytest.raises(ConflitoDadosError):
            await service.vincular_pessoa(abordagem.id, pessoa.id, usuario)


class TestVincularVeiculo:
    """Testes de vincular_veiculo, incluindo o tratamento de corrida no insert."""

    async def test_vincular_veiculo_corrida_no_insert_gera_conflito_dados(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
        veiculo: Veiculo,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Corrida entre duas requisições vinculando o mesmo veículo pela 1a vez.

        Mesmo cenário de test_vincular_pessoa_corrida_no_insert_gera_conflito_dados,
        para uq_abordagem_veiculo.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário (dono da abordagem).
            veiculo: Fixture de veículo a vincular.
            monkeypatch: Fixture do pytest para substituir buscar_detalhe.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(data_hora=datetime.now(UTC), endereco_texto="Rua Teste, 200")
        abordagem = await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)
        await service.vincular_veiculo(abordagem.id, veiculo.id, usuario)

        abordagem_desatualizada = SimpleNamespace(
            id=abordagem.id, usuario_id=usuario.id, veiculos=[], data_hora=abordagem.data_hora
        )

        async def buscar_detalhe_desatualizado(*args, **kwargs):
            return abordagem_desatualizada

        monkeypatch.setattr(service, "buscar_detalhe", buscar_detalhe_desatualizado)

        with pytest.raises(ConflitoDadosError):
            await service.vincular_veiculo(abordagem.id, veiculo.id, usuario)


class TestListarPorUsuario:
    """Testes de listagem de abordagens por usuário."""

    async def test_listar_retorna_apenas_abordagens_do_usuario(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que listar retorna apenas abordagens do usuário logado.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        service = AbordagemService(db_session)
        data = AbordagemCreate(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua A, 1",
        )
        await service.criar(data=data, user_id=usuario.id, guarnicao_id=guarnicao.id)

        result = await service.listar_por_usuario(
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(result) == 1
        assert result[0].usuario_id == usuario.id
        assert all(a.usuario_id == usuario.id for a in result)

    async def test_listar_nao_retorna_abordagens_de_outro_usuario(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Testa que abordagens de outro usuário não aparecem na listagem.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        outro_usuario = Usuario(
            nome="Outro",
            matricula="9999999",
            senha_hash="x",
            guarnicao_id=guarnicao.id,
        )
        db_session.add(outro_usuario)
        await db_session.flush()

        service = AbordagemService(db_session)
        data = AbordagemCreate(data_hora=datetime.now(UTC))
        await service.criar(data=data, user_id=outro_usuario.id, guarnicao_id=guarnicao.id)

        result = await service.listar_por_usuario(
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert len(result) == 0


class TestListarPorData:
    """Testes de listagem de abordagens filtradas por data."""

    async def test_listar_abordagens_com_filtro_data(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Retorna apenas abordagens do dia informado.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import timedelta

        from app.models.abordagem import Abordagem

        hoje = datetime.now(UTC)
        ontem = datetime(hoje.year, hoje.month, hoje.day, 10, 0, tzinfo=UTC) - timedelta(days=1)

        a_hoje = Abordagem(
            data_hora=datetime(hoje.year, hoje.month, hoje.day, 10, 0, tzinfo=UTC),
            endereco_texto="Rua Hoje, 1",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        a_ontem = Abordagem(
            data_hora=ontem,
            endereco_texto="Rua Ontem, 2",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add_all([a_hoje, a_ontem])
        await db_session.flush()

        service = AbordagemService(db_session)
        result = await service.listar_por_data(
            guarnicao_id=guarnicao.id,
            data=datetime.now(UTC).date(),
        )
        assert len(result) == 1
        assert result[0].endereco_texto == "Rua Hoje, 1"

    async def test_listar_abordagens_data_sem_resultados(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Retorna lista vazia para dia sem abordagens.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import date, timedelta

        service = AbordagemService(db_session)
        data_futura = date.today() + timedelta(days=365)
        result = await service.listar_por_data(
            guarnicao_id=guarnicao.id,
            data=data_futura,
        )
        assert result == []


class TestListarPorPessoa:
    """Testes de listagem de abordagens pela ficha da pessoa."""

    async def test_ficha_pessoa_retorna_abordagem_de_outra_guarnicao(
        self,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
        bpm: Bpm,
    ):
        """Abordagem de qualquer guarnição deve aparecer na ficha da pessoa.

        O isolamento de guarnição não se aplica à ficha individual de uma
        pessoa — usuários devem ver todas as abordagens dela, independente
        de qual guarnição registrou.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Guarnição A (do usuário que registrou).
            usuario: Usuário da guarnição A.
            bpm: BPM para criar a guarnição B (visualizadora).
        """
        guarnicao_b = Guarnicao(nome="Cia Vizinha", bpm_id=bpm.id, codigo="VIZ-001")
        db_session.add(guarnicao_b)
        await db_session.flush()

        pessoa = Pessoa(nome="Abordado Teste", guarnicao_id=guarnicao.id)
        db_session.add(pessoa)
        await db_session.flush()

        abordagem = Abordagem(
            data_hora=datetime.now(UTC),
            endereco_texto="Rua A, 1",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(abordagem)
        await db_session.flush()

        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        await db_session.flush()

        service = AbordagemService(db_session)
        # Consulta como usuário da guarnição B — deve ver abordagem da guarnição A
        resultado = await service.listar_por_pessoa(pessoa.id, guarnicao_b.id)
        assert len(resultado) == 1, "Ficha da pessoa deve mostrar abordagens de qualquer guarnição"


@pytest.mark.asyncio
async def test_listar_com_bpm_id_chama_repo_by_bpm(
    db_session: AsyncSession, bpm, guarnicao, usuario
):
    """listar() com guarnicao_id=None e bpm_id definido filtra por BPM."""
    from datetime import UTC, datetime

    from app.models.abordagem import Abordagem

    a = Abordagem(
        guarnicao_id=guarnicao.id,
        usuario_id=usuario.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av Teste",
    )
    db_session.add(a)
    await db_session.flush()

    service = AbordagemService(db_session)
    result = await service.listar(guarnicao_id=None, bpm_id=bpm.id)
    assert any(ab.id == a.id for ab in result)


@pytest.mark.asyncio
async def test_listar_sem_filtro_retorna_global(db_session: AsyncSession, guarnicao, usuario):
    """listar() com guarnicao_id=None e bpm_id=None retorna todas as abordagens."""
    from datetime import UTC, datetime

    from app.models.abordagem import Abordagem

    a = Abordagem(
        guarnicao_id=guarnicao.id,
        usuario_id=usuario.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av Global",
    )
    db_session.add(a)
    await db_session.flush()

    service = AbordagemService(db_session)
    result = await service.listar(guarnicao_id=None, bpm_id=None)
    assert any(ab.id == a.id for ab in result)


class TestVerificarEscopo:
    """Testes de AbordagemService.verificar_escopo (revisão pós-#22/2026-07-13).

    Checagem leve de autorização (sem eager load) que substituiu o uso de
    buscar_detalhe só para validar escopo em fotos.py/ocorrencia_service.py —
    mesma regra de prioridade (guarnicao_id > bpm_id > global).
    """

    async def test_nao_levanta_quando_abordagem_esta_na_guarnicao(
        self, db_session: AsyncSession, guarnicao: Guarnicao, abordagem: Abordagem
    ):
        """Não levanta erro quando a abordagem pertence à guarnição informada."""
        service = AbordagemService(db_session)
        await service.verificar_escopo(abordagem.id, guarnicao.id)

    async def test_levanta_quando_abordagem_e_de_outra_guarnicao(
        self, db_session: AsyncSession, abordagem: Abordagem
    ):
        """Levanta NaoEncontradoError quando a abordagem é de outra guarnição."""
        service = AbordagemService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.verificar_escopo(abordagem.id, guarnicao_id=999999)

    async def test_nao_levanta_quando_abordagem_esta_no_bpm(
        self, db_session: AsyncSession, abordagem: Abordagem, guarnicao: Guarnicao
    ):
        """Escopo por BPM (guarnicao_id=None) aceita abordagem de guarnição do mesmo BPM."""
        service = AbordagemService(db_session)
        await service.verificar_escopo(abordagem.id, guarnicao_id=None, bpm_id=guarnicao.bpm_id)

    async def test_levanta_quando_abordagem_e_de_outro_bpm(
        self, db_session: AsyncSession, abordagem: Abordagem
    ):
        """Levanta NaoEncontradoError quando a abordagem é de guarnição de outro BPM."""
        service = AbordagemService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.verificar_escopo(abordagem.id, guarnicao_id=None, bpm_id=999999)

    async def test_nao_levanta_em_escopo_global(
        self, db_session: AsyncSession, abordagem: Abordagem
    ):
        """Sem guarnicao_id nem bpm_id (equipe sem isolamento), aceita qualquer abordagem ativa."""
        service = AbordagemService(db_session)
        await service.verificar_escopo(abordagem.id, guarnicao_id=None, bpm_id=None)

    async def test_levanta_quando_abordagem_nao_existe(
        self, db_session: AsyncSession, guarnicao: Guarnicao
    ):
        """Levanta NaoEncontradoError para abordagem_id inexistente."""
        service = AbordagemService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.verificar_escopo(999999, guarnicao.id)
