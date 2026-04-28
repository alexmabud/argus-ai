"""Testes de integração dos endpoints de listagem de abordagens."""

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


class TestListarAbordagens:
    """Testes do endpoint GET /abordagens/."""

    async def test_listar_retorna_minhas_abordagens(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Testa que o endpoint retorna as abordagens do usuário autenticado.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
            abordagem: Fixture de abordagem criada.
        """
        response = await client.get("/api/v1/abordagens/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == abordagem.id

    async def test_listar_requer_autenticacao(self, client: AsyncClient):
        """Testa que o endpoint requer token JWT.

        Args:
            client: Cliente HTTP de teste.
        """
        response = await client.get("/api/v1/abordagens/")
        assert response.status_code == 401


class TestDetalheAbordagem:
    """Testes do endpoint GET /abordagens/{abordagem_id}."""

    async def test_detalhe_retorna_abordagem_completa(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Testa que o detalhe retorna dados completos com relacionamentos.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
            abordagem: Fixture de abordagem criada.
        """
        response = await client.get(f"/api/v1/abordagens/{abordagem.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == abordagem.id
        assert "pessoas" in data
        assert "veiculos" in data
        assert "fotos" in data
        assert "ocorrencias" in data

    async def test_detalhe_404_abordagem_inexistente(self, client: AsyncClient, auth_headers: dict):
        """Testa que detalhe de abordagem inexistente retorna 404.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
        """
        response = await client.get("/api/v1/abordagens/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_listar_retorna_403_sem_guarnicao(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Testa que listagem retorna 403 para usuário sem guarnição.

        Args:
            client: Cliente HTTP de teste.
            db_session: Sessão do banco de testes.
        """
        from app.core.security import criar_access_token, hash_senha
        from app.models.usuario import Usuario as UsuarioModel

        # Criar usuário sem guarnição, com session_id para autenticação passar
        usuario_sem_guarnicao = UsuarioModel(
            nome="Sem Guarnicao",
            matricula="0000001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=None,
            session_id="session-sem-guarnicao",
        )
        db_session.add(usuario_sem_guarnicao)
        await db_session.flush()

        token = criar_access_token(
            {"sub": str(usuario_sem_guarnicao.id), "sid": "session-sem-guarnicao"}
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/abordagens/", headers=headers)
        assert response.status_code == 403


class TestListarAbordagensPorData:
    """Testes do parâmetro ?data no endpoint GET /abordagens/."""

    async def test_listar_com_filtro_data_retorna_do_dia(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Com ?data=HOJE, retorna apenas abordagens do dia.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import timedelta

        hoje = datetime.now(UTC)
        a_hoje = Abordagem(
            data_hora=datetime(hoje.year, hoje.month, hoje.day, 9, 0, tzinfo=UTC),
            endereco_texto="Rua do Dia, 10",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        a_ontem = Abordagem(
            data_hora=datetime(hoje.year, hoje.month, hoje.day, 9, 0, tzinfo=UTC)
            - timedelta(days=1),
            endereco_texto="Rua de Ontem, 5",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add_all([a_hoje, a_ontem])
        await db_session.flush()

        data_str = hoje.strftime("%Y-%m-%d")
        resp = await client.get(f"/api/v1/abordagens/?data={data_str}", headers=auth_headers)
        assert resp.status_code == 200
        result = resp.json()
        assert isinstance(result, list)
        enderecos = [r["endereco_texto"] for r in result]
        assert "Rua do Dia, 10" in enderecos
        assert "Rua de Ontem, 5" not in enderecos

    async def test_listar_sem_filtro_data_retorna_paginado(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Sem ?data, comportamento paginado original não é afetado.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
            abordagem: Fixture de abordagem.
        """
        resp = await client.get("/api/v1/abordagens/", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    async def test_listar_com_data_invalida_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """?data com formato inválido retorna 422.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
        """
        resp = await client.get("/api/v1/abordagens/?data=nao-e-data", headers=auth_headers)
        assert resp.status_code == 422
