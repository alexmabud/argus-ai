"""Testes de integração para o endpoint /api/v1/localidades."""

from httpx import AsyncClient


class TestListarEstados:
    """Testes para GET /localidades?tipo=estado."""

    async def test_retorna_27_estados(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar os 27 estados brasileiros."""
        response = await client.get(
            "/api/v1/localidades?tipo=estado",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 27
        assert all(e["tipo"] == "estado" for e in data)

    async def test_sem_autenticacao_retorna_401(self, client: AsyncClient):
        """Deve retornar 401 sem token."""
        response = await client.get("/api/v1/localidades?tipo=estado")
        assert response.status_code == 401


class TestCriarLocalidade:
    """Testes para POST /localidades."""

    async def test_criar_cidade(self, client: AsyncClient, auth_headers: dict):
        """Deve criar cidade vinculada a um estado."""
        estados = (await client.get("/api/v1/localidades?tipo=estado", headers=auth_headers)).json()
        sp = next((e for e in estados if e["sigla"] == "SP"), None)
        assert sp is not None, "Estado SP não encontrado — verifique o seed no conftest"

        response = await client.post(
            "/api/v1/localidades",
            json={"nome": "Campinas", "tipo": "cidade", "parent_id": sp["id"]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["nome_exibicao"] == "Campinas"

    async def test_criar_duplicata_retorna_409(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 409 ao criar cidade duplicada."""
        estados = (await client.get("/api/v1/localidades?tipo=estado", headers=auth_headers)).json()
        sp = next((e for e in estados if e["sigla"] == "SP"), None)
        assert sp is not None, "Estado SP não encontrado — verifique o seed no conftest"

        payload = {"nome": "São Paulo", "tipo": "cidade", "parent_id": sp["id"]}
        await client.post("/api/v1/localidades", json=payload, headers=auth_headers)
        response = await client.post("/api/v1/localidades", json=payload, headers=auth_headers)
        assert response.status_code == 409
