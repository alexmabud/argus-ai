"""Serviço de geocoding reverso para obter endereço a partir de coordenadas.

Converte coordenadas GPS (latitude/longitude) em endereços legíveis
usando Nominatim (OpenStreetMap, gratuito) ou Google Maps (pago).
Falhas nunca bloqueiam operações — geocoding é best-effort.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger("argus")


class GeocodingService:
    """Serviço de geocoding reverso.

    Converte coordenadas GPS em endereço textual usando provedor
    configurado (Nominatim ou Google Maps). Tratamento de erros
    garante que falhas nunca bloqueiam operações do sistema.
    """

    async def reverse(self, lat: float, lon: float) -> str | None:
        """Obtém endereço a partir de coordenadas GPS.

        Despacha para provedor configurado em settings.GEOCODING_PROVIDER.
        Retorna None silenciosamente em caso de falha (best-effort).

        Args:
            lat: Latitude GPS.
            lon: Longitude GPS.

        Returns:
            Endereço legível ou None se falha.
        """
        try:
            if settings.GEOCODING_PROVIDER == "google":
                return await self._google_reverse(lat, lon)
            return await self._nominatim_reverse(lat, lon)
        except Exception:
            logger.warning("Falha no geocoding reverso: lat=%s, lon=%s", lat, lon)
            return None

    async def _nominatim_reverse(self, lat: float, lon: float) -> str | None:
        """Geocoding reverso via Nominatim (OpenStreetMap).

        Respeita política de 1 req/s do Nominatim com timeout de 5 segundos.

        Args:
            lat: Latitude GPS.
            lon: Longitude GPS.

        Returns:
            Endereço formatado ou None se falha.
        """
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }
        headers = {"User-Agent": "ArgusAI/2.0"}

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("display_name")

    async def _google_reverse(self, lat: float, lon: float) -> str | None:
        """Geocoding reverso via Google Maps Geocoding API.

        Requer GOOGLE_MAPS_API_KEY configurado em settings.

        Args:
            lat: Latitude GPS.
            lon: Longitude GPS.

        Returns:
            Endereço formatado ou None se falha.
        """
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat},{lon}",
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "pt-BR",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if results:
                return results[0].get("formatted_address")
            return None
