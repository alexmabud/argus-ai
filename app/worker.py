"""Worker arq para processamento assíncrono de tarefas pesadas.

Configura e executa o worker arq com Redis como broker de mensagens.
Registra tasks de processamento de PDF (OCR + extração de texto)
e processamento facial (InsightFace).

Uso:
    make worker  # ou: arq app.worker.WorkerSettings
"""

import logging

from arq.connections import RedisSettings

from app.config import settings
from app.core.logging_config import setup_logging
from app.tasks.face_processor import processar_face_task
from app.tasks.pdf_processor import processar_pdf_task
from app.tasks.thumbnail_backfill import gerar_thumbnail_backfill_task

logger = logging.getLogger("argus")


async def startup(ctx: dict) -> None:
    """Inicializa recursos compartilhados do worker.

    Carrega EmbeddingService (SentenceTransformers), FaceService (InsightFace)
    em memória e cria sessão de banco de dados disponível para todas as tasks.

    Args:
        ctx: Contexto compartilhado do worker arq.
    """
    from app.database.session import AsyncSessionLocal
    from app.services.embedding_service import EmbeddingService
    from app.services.storage_service import StorageService

    # Sem isso, o worker roda sem logging.basicConfig() nenhum: todo
    # logger.info (inclusive das tasks de foto/PDF) é descartado em silêncio,
    # porque o root logger sem config fica em WARNING por padrão. Só a API
    # chamava setup_logging() (app/main.py), deixando o worker cego para
    # diagnóstico de incidentes (achado 2026-07-15, investigação do
    # alert-worker-parado).
    setup_logging()
    logger.info("Iniciando worker arq...")

    try:
        ctx["embedding_service"] = EmbeddingService()
    except Exception as exc:
        logger.warning("EmbeddingService indisponível: %s", exc)
        ctx["embedding_service"] = None

    # Face service é opcional — requer insightface
    try:
        from app.services.face_service import FaceService

        ctx["face_service"] = FaceService()
    except Exception as exc:
        logger.warning("FaceService indisponível: %s", exc)
        ctx["face_service"] = None

    # Cliente S3 singleton — reutiliza TCP/TLS entre tasks.
    await StorageService.get().startup()
    ctx["storage"] = StorageService.get()

    ctx["db_session_factory"] = AsyncSessionLocal
    logger.info("Worker arq pronto")


async def shutdown(ctx: dict) -> None:
    """Finaliza recursos do worker.

    Args:
        ctx: Contexto compartilhado do worker arq.
    """
    from app.services.storage_service import StorageService

    logger.info("Encerrando worker arq...")
    await StorageService.get().shutdown()


def _parse_redis_settings() -> RedisSettings:
    """Converte REDIS_URL em RedisSettings do arq.

    Suporta formatos:
        - redis://host:port/db
        - redis://:password@host:port/db

    Returns:
        Configurações Redis para o worker arq.
    """
    from urllib.parse import urlparse

    parsed = urlparse(settings.REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:
    """Configurações do worker arq.

    Define funções registradas, callbacks de ciclo de vida e
    configuração de conexão Redis.

    Attributes:
        functions: Lista de funções assíncronas executáveis pelo worker.
        on_startup: Callback chamado na inicialização.
        on_shutdown: Callback chamado no encerramento.
        redis_settings: Configurações de conexão Redis.
        max_jobs: Número máximo de jobs simultâneos.
        job_timeout: Timeout máximo por job em segundos (10 min).
    """

    functions = [processar_pdf_task, processar_face_task, gerar_thumbnail_backfill_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _parse_redis_settings()
    max_jobs = 5
    job_timeout = 600  # 10 minutos
    max_tries = 3  # retry automático em caso de falha
    # Health-check por instância (achado #12/2026-07-13): com WORKER_ID setado
    # (docker-compose.prod.yml define um valor distinto por worker/worker-2),
    # cada processo grava sua própria chave no Redis em vez de todos
    # compartilharem "arq:queue:health-check" — o último a escrever "esconde"
    # os outros mortos. Sem WORKER_ID (dev, 1 worker só), mantém o default do arq.
    # Intervalo curto (default do arq é 3600s) para a métrica refletir a
    # realidade em minutos, não em horas.
    health_check_interval = 60
    if settings.WORKER_ID:
        health_check_key = f"arq:health-check:{settings.WORKER_ID}"
