"""Router de geocoding reverso — proxy autenticado para o provedor externo.

Evita que o navegador de cada agente envie coordenadas precisas de operações
direto ao Nominatim/OSM: o backend faz a chamada externa (egress único,
User-Agent correto) e devolve apenas o endereço textual ao cliente.
"""

from fastapi import APIRouter, Depends, Query, Request

from app.core.rate_limit import limiter
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.geocoding_service import GeocodingService

router = APIRouter(prefix="/geocode", tags=["Geocode"])


@router.get("/reverse")
@limiter.limit("30/minute")
async def reverse_geocode(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    _: Usuario = Depends(get_current_user),
) -> dict:
    """Resolve um endereço textual a partir de coordenadas GPS.

    Proxy autenticado: o backend chama o provedor de geocoding configurado
    (Nominatim/Google) e retorna apenas o endereço, sem expor as coordenadas
    do agente diretamente ao serviço externo. Best-effort — retorna
    ``endereco=None`` em caso de falha (geocoding nunca bloqueia operações).

    Args:
        request: Objeto Request do FastAPI (necessário ao rate limiter).
        lat: Latitude GPS (-90..90).
        lon: Longitude GPS (-180..180).

    Returns:
        Dict com a chave ``endereco`` (str com o endereço ou None).
    """
    endereco = await GeocodingService().reverse(lat, lon)
    return {"endereco": endereco}
