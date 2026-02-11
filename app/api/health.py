"""Router de verificação de saúde da aplicação.

Fornece endpoint de health check para monitoramento da disponibilidade
e status da API do Argus AI.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica a saúde e disponibilidade da aplicação.

    Endpoint simples que retorna o status da aplicação. Útil para
    health checks em orchestradores como Kubernetes, load balancers
    ou monitoramento.

    Returns:
        dict: Dicionário com status da aplicação.
            - status: "ok" se a aplicação está funcionando.
            - service: Nome da aplicação ("Argus AI").

    Raises:
        Nenhuma. Sempre retorna sucesso se a aplicação está respondendo.
    """
    return {"status": "ok", "service": "Argus AI"}
