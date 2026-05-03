"""Testes de integração da API de Analytics.

Testa endpoints de métricas operacionais do dashboard.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario

_BRT = ZoneInfo("America/Sao_Paulo")


class TestPessoasRecorrentes:
    """Testes do endpoint GET /api/v1/analytics/pessoas-recorrentes."""

    async def test_pessoas_recorrentes_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pessoas (pode ser vazia).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/pessoas-recorrentes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestResumoHoje:
    """Testes do endpoint GET /api/v1/analytics/resumo-hoje."""

    async def test_resumo_hoje_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-hoje", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data

    async def test_resumo_hoje_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/analytics/resumo-hoje")
        assert response.status_code == 401


class TestResumoMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-mes."""

    async def test_resumo_mes_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-mes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestResumoTotalEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-total."""

    async def test_resumo_total_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar totais históricos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/resumo-total", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestPorDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-dia."""

    async def test_por_dia_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-dia", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_por_dia_aceita_parametro_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar parâmetro dias.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-dia?dias=7", headers=auth_headers)
        assert response.status_code == 200


class TestPorMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-mes."""

    async def test_por_mes_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get("/api/v1/analytics/por-mes", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDiasComAbordagemEndpoint:
    """Testes do endpoint GET /api/v1/analytics/dias-com-abordagem."""

    async def test_retorna_lista_de_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de dias com abordagem no mês.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=2026-03",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_mes_invalido_retorna_422(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 422 para formato de mês inválido.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=invalido",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestPessoasDoDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/pessoas-do-dia."""

    async def test_retorna_lista_de_pessoas(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pessoas abordadas no dia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/analytics/pessoas-do-dia?data=2026-03-14",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAbordagensDoDia:
    """Testes de integração para GET /analytics/abordagens-do-dia."""

    async def test_retorna_pontos_do_dia(
        self, client: AsyncClient, auth_headers: dict, abordagem: Abordagem
    ):
        """Deve retornar pontos do dia com lat, lng e horario.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            abordagem: Fixture de abordagem com coordenadas associada à guarnição.
        """
        data = abordagem.data_hora.astimezone(_BRT).date().isoformat()
        resp = await client.get(
            f"/api/v1/analytics/abordagens-do-dia?data={data}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        pontos = resp.json()
        assert isinstance(pontos, list)
        assert len(pontos) >= 1
        assert "lat" in pontos[0]
        assert "lng" in pontos[0]
        assert "horario" in pontos[0]

    async def test_dia_sem_abordagens_retorna_lista_vazia(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Deve retornar lista vazia para dia sem abordagens.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        resp = await client.get(
            "/api/v1/analytics/abordagens-do-dia?data=2000-01-01",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requer_autenticacao(self, client: AsyncClient):
        """Deve retornar 401 sem token.

        Args:
            client: Cliente HTTP assincrónico.
        """
        resp = await client.get("/api/v1/analytics/abordagens-do-dia?data=2026-03-28")
        assert resp.status_code == 401


@pytest.fixture
async def equipe_b(db_session: AsyncSession, bpm) -> Guarnicao:
    """Segunda equipe sem isolamento (toggle OFF).

    Args:
        db_session: Sessão do banco de testes.
        bpm: BPM pai da equipe.

    Returns:
        Guarnicao: Objeto de guarnição com isolamento_abordagens=False.
    """
    g = Guarnicao(nome="GU Bravo", bpm_id=bpm.id, codigo="2BPM-GUB")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_b(db_session: AsyncSession, equipe_b: Guarnicao) -> Usuario:
    """Usuário da equipe B.

    Args:
        db_session: Sessão do banco de testes.
        equipe_b: Fixture da segunda equipe.

    Returns:
        Usuario: Objeto de usuário vinculado à equipe B.
    """
    u = Usuario(
        nome="Agente B",
        matricula="BBB001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=equipe_b.id,
        session_id="session-b",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_b(usuario_b: Usuario) -> dict:
    """Headers do usuário B.

    Args:
        usuario_b: Fixture do usuário da equipe B.

    Returns:
        dict: Headers com Authorization Bearer token para o usuário B.
    """
    token = criar_access_token(
        {
            "sub": str(usuario_b.id),
            "guarnicao_id": usuario_b.guarnicao_id,
            "sid": usuario_b.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def abordagem_equipe_a(
    db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
) -> Abordagem:
    """Abordagem registrada pela equipe A (guarnicao padrão do conftest).

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição padrão (equipe A).
        usuario: Fixture de usuário da equipe A.

    Returns:
        Abordagem: Objeto de abordagem associado à equipe A.
    """
    a = Abordagem(
        guarnicao_id=guarnicao.id,
        usuario_id=usuario.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Rua A 100",
    )
    db_session.add(a)
    await db_session.flush()
    return a


class TestAnalyticsToggleIsolamento:
    """Toggle de isolamento deve afetar analytics."""

    async def test_resumo_total_toggle_off_ve_global(
        self,
        client: AsyncClient,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        guarnicao: Guarnicao,
        equipe_b: Guarnicao,
    ):
        """Usuário da equipe B com toggle OFF vê abordagens da equipe A no resumo total.

        Args:
            client: Cliente HTTP assincrónico.
            headers_b: Headers com token do usuário B.
            abordagem_equipe_a: Abordagem registrada pela equipe A.
            guarnicao: Fixture da equipe A.
            equipe_b: Fixture da equipe B com toggle OFF.
        """
        assert equipe_b.isolamento_abordagens is False
        response = await client.get("/api/v1/analytics/resumo-total", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        # equipe B tem 0 abordagens próprias, toggle OFF = global → deve ver a da equipe A
        assert data["abordagens"] >= 1

    async def test_resumo_total_toggle_on_nao_ve_outra_equipe(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        equipe_b: Guarnicao,
    ):
        """Usuário da equipe B com toggle ON não vê abordagens da equipe A.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de testes.
            headers_b: Headers com token do usuário B.
            abordagem_equipe_a: Abordagem registrada pela equipe A.
            equipe_b: Fixture da equipe B com toggle ativado para ON.
        """
        equipe_b.isolamento_abordagens = True
        await db_session.flush()
        response = await client.get("/api/v1/analytics/resumo-total", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        assert data["abordagens"] == 0

    async def test_dias_com_abordagem_toggle_off_ve_global(
        self,
        client: AsyncClient,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        equipe_b: Guarnicao,
    ):
        """dias_com_abordagem com toggle OFF inclui dias de outras equipes.

        Args:
            client: Cliente HTTP assincrónico.
            headers_b: Headers com token do usuário B.
            abordagem_equipe_a: Abordagem registrada pela equipe A no mês atual.
            equipe_b: Fixture da equipe B com toggle OFF.
        """
        mes_atual = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m")
        assert equipe_b.isolamento_abordagens is False
        response = await client.get(
            f"/api/v1/analytics/dias-com-abordagem?mes={mes_atual}",
            headers=headers_b,
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_resumo_hoje_toggle_off_ve_global(
        self,
        client: AsyncClient,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        equipe_b: Guarnicao,
    ):
        """resumo_hoje com toggle OFF conta abordagens de outras equipes.

        Args:
            client: Cliente HTTP assincrónico.
            headers_b: Headers com token do usuário B.
            abordagem_equipe_a: Abordagem registrada pela equipe A hoje.
            equipe_b: Fixture da equipe B com toggle OFF.
        """
        assert equipe_b.isolamento_abordagens is False
        response = await client.get("/api/v1/analytics/resumo-hoje", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        assert data["abordagens"] >= 1
