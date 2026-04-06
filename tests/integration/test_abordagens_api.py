"""Testes de integração dos endpoints de listagem de abordagens."""

from httpx import AsyncClient

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
