"""Testes de integração da API de Veículos.

Testa endpoints de listagem, criação e autocomplete de veículos.
"""

from httpx import AsyncClient

from app.models.veiculo import Veiculo


class TestListarVeiculos:
    """Testes do endpoint GET /api/v1/veiculos/."""

    async def test_listar_veiculos_retorna_200(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa listagem de veículos retorna 200 com dados.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo.
        """
        response = await client.get("/api/v1/veiculos/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_buscar_veiculo_por_placa(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa busca por placa retorna veículo correto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com placa ABC1D23.
        """
        response = await client.get(
            "/api/v1/veiculos/", params={"placa": "ABC1"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "ABC1D23" in data[0]["placa"]

    async def test_listar_veiculos_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/veiculos/")
        assert response.status_code == 401


class TestCriarVeiculo:
    """Testes do endpoint POST /api/v1/veiculos/."""

    async def test_criar_veiculo_retorna_201(self, client: AsyncClient, auth_headers: dict):
        """Testa criação de veículo retorna 201.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={
                "placa": "XYZ9A87",
                "modelo": "Civic",
                "cor": "Preto",
                "ano": 2022,
                "tipo": "Carro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["placa"] == "XYZ9A87"

    async def test_criar_veiculo_placa_duplicada_retorna_409(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que placa duplicada retorna 409.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com placa ABC1D23.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={
                "placa": "ABC1D23",
                "modelo": "Palio",
                "cor": "Vermelho",
                "ano": 2018,
                "tipo": "Carro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_criar_veiculo_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que criação sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={"placa": "AAA1A11", "modelo": "Uno", "cor": "Azul"},
        )
        assert response.status_code == 401


class TestLocalidadesVeiculos:
    """Testes do endpoint GET /api/v1/veiculos/localidades."""

    async def test_listar_localidades_retorna_200(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa autocomplete de modelos e cores retorna 200.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo para popular dados.
        """
        response = await client.get("/api/v1/veiculos/localidades", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "modelos" in data
        assert "cores" in data
