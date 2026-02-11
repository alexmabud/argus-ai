"""Configuração de logging para a aplicação.

Inicializa o sistema de logging com formato padronizado, nível adequado
conforme modo debug/produção, e reduz verbosidade de bibliotecas externas.
"""

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """Configura logging da aplicação no inicialização.

    Define formato padronizado com timestamp, nível, nome do logger e mensagem.
    Nível é DEBUG em modo debug ou INFO em produção. Reduz logs verbosos de
    uvicorn.access e sqlalchemy.engine para evitar ruído em logs.

    O logging é inicializado no startup da aplicação via lifespan hook.
    """

    level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduzir ruído de libs externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
