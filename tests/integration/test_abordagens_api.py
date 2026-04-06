"""Testes de integração dos endpoints de listagem de abordagens."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem


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
