"""Testes de integração da API de Abordagens.

Testa endpoints de criação de abordagem completa, vinculação de
pessoas e veículos, e fluxo de abordagem em campo.
"""

from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.pessoa import Pessoa


class TestCriarAbordagem:
    """Testes do endpoint POST /api/v1/abordagens/."""

    async def test_criar_abordagem_basica(self, client: AsyncClient, auth_headers: dict):
        """Testa criação de abordagem simples retorna 201.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "latitude": -22.9068,
                "longitude": -43.1729,
                "endereco_texto": "Av. Brasil, 1000 - Centro, RJ",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["endereco_texto"] == "Av. Brasil, 1000 - Centro, RJ"
        assert "id" in data

    async def test_criar_abordagem_com_pessoa(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa criação de abordagem com pessoa vinculada.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua com Pessoa",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    async def test_criar_abordagem_sem_auth_retorna_403(self, client: AsyncClient):
        """Testa que requisição sem token retorna 403.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Sem Auth",
            },
        )
        assert response.status_code == 403


class TestListarAbordagens:
    """Testes do endpoint GET /api/v1/abordagens/."""

    async def test_listar_abordagens(self, client: AsyncClient, auth_headers: dict):
        """Testa listagem de abordagens retorna lista.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/abordagens/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDetalheAbordagem:
    """Testes do endpoint GET /api/v1/abordagens/{id}."""

    async def test_obter_detalhe_abordagem(self, client: AsyncClient, auth_headers: dict):
        """Testa obtenção de detalhe com pessoas, veículos e passagens.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        create_response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua Detalhe, 100",
            },
            headers=auth_headers,
        )
        abordagem_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/abordagens/{abordagem_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "pessoas" in data
        assert "veiculos" in data
        assert "passagens" in data

    async def test_obter_abordagem_inexistente(self, client: AsyncClient, auth_headers: dict):
        """Testa busca de abordagem inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/abordagens/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestVincularPessoa:
    """Testes dos endpoints de vinculação pessoa ↔ abordagem."""

    async def test_vincular_e_desvincular_pessoa(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa vincular e desvincular pessoa de abordagem.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa.
        """
        # Criar abordagem
        create = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua Vinculo",
            },
            headers=auth_headers,
        )
        abordagem_id = create.json()["id"]

        # Vincular pessoa
        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Desvincular pessoa
        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
