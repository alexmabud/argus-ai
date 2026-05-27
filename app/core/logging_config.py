"""Configuração de logging para a aplicação.

Inicializa o sistema de logging com formato padronizado, nível adequado
conforme modo debug/produção, e reduz verbosidade de bibliotecas externas.
Inclui filtro de redação de PII e secrets para evitar vazamento LGPD em
agregadores de log (Loki, Telegram, journald).
"""

import logging
import re
import sys

from app.config import settings


class RedactFilter(logging.Filter):
    """Mascara PII e secrets em mensagens de log antes de emitir.

    Aplica padroes para JWT (Bearer + isolado), CPF formatado e campos
    `senha`/`password` em payloads JSON. Roda sobre `record.getMessage()`
    apos a formatacao para capturar mensagens com args ja interpolados.
    """

    PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"(authorization:\s*bearer\s+)[\w\-\.]+", re.IGNORECASE), r"\1***REDACTED***"),
        (re.compile(r'("senha"\s*:\s*)"[^"]+"'), r'\1"***REDACTED***"'),
        (re.compile(r'("password"\s*:\s*)"[^"]+"'), r'\1"***REDACTED***"'),
        (re.compile(r"\beyJ[\w\-]+\.[\w\-]+\.[\w\-]+"), "***JWT_REDACTED***"),
        (re.compile(r"(\d{3})\.\d{3}\.\d{3}-(\d{2})"), r"\1.***.***-\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Aplica os padroes de redacao a mensagem do record.

        Returns:
            True sempre (filtro nao descarta records, so transforma).
        """
        try:
            msg = record.getMessage()
        except Exception:
            return True
        original = msg
        for pattern, repl in self.PATTERNS:
            msg = pattern.sub(repl, msg)
        if msg != original:
            record.msg = msg
            record.args = ()
        return True


def setup_logging() -> None:
    """Configura logging da aplicação no inicialização.

    Define formato padronizado com timestamp, nível, nome do logger e mensagem.
    Nível é DEBUG em modo debug ou INFO em produção. Reduz logs verbosos de
    uvicorn.access e sqlalchemy.engine para evitar ruído em logs. Instala
    RedactFilter em handlers root e loggers conhecidos por logarem payloads.

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

    # Instalar filtro de redacao de PII/secrets em todos os handlers root
    # e em loggers conhecidos por logarem payloads.
    redact = RedactFilter()
    for handler in logging.root.handlers:
        handler.addFilter(redact)
    for nome in ("uvicorn.access", "sqlalchemy.engine", "argus"):
        logging.getLogger(nome).addFilter(redact)
