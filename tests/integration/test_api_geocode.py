"""Testes de integração do proxy de geocoding reverso (/geocode/reverse).

Valida que o geocoding passa pelo backend (não direto do cliente ao OSM),
exige autenticação e valida os limites das coordenadas — achado #12 do
Sub-lote 2C.
"""

from httpx import AsyncClient

from app.services.geocoding_service import GeocodingService


class TestGeocodeReverse:
    """Testes do endpoint GET /api/v1/geocode/reverse."""

    async def test_reverse_autenticado_retorna_endereco(
        self, client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        """Proxy autenticado deve retornar o endereço resolvido pelo backend.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            monkeypatch: Fixture pytest para substituir o provedor externo.
        """

        async def fake_reverse(self, lat, lon):
            return "Rua X, 10, Centro, Cidade"

        monkeypatch.setattr(GeocodingService, "reverse", fake_reverse)

        resp = await client.get("/api/v1/geocode/reverse?lat=-23.5&lon=-46.6", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["endereco"] == "Rua X, 10, Centro, Cidade"

    async def test_reverse_sem_auth_retorna_401(self, client: AsyncClient):
        """Sem JWT, o proxy não pode ser usado (evita proxy aberto).

        Args:
            client: Cliente HTTP assíncrono.
        """
        resp = await client.get("/api/v1/geocode/reverse?lat=-23.5&lon=-46.6")
        assert resp.status_code == 401

    async def test_reverse_coordenadas_invalidas_retorna_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Coordenadas fora dos limites devem retornar 422.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
        """
        resp = await client.get("/api/v1/geocode/reverse?lat=999&lon=0", headers=auth_headers)
        assert resp.status_code == 422
