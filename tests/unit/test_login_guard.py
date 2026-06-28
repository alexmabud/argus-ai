"""Testes do guard de brute-force de login por IP (login_guard).

Cobre a política de fail-open (D-G2-1): quando o Redis está indisponível, o
bloqueio por IP é desativado e o login é permitido (lockout por conta no DB
segue como defesa primária), mas o evento deve ser registrado em nível ERROR
para visibilidade operacional.
"""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.core import login_guard


@pytest.mark.asyncio
async def test_ip_bloqueado_failopen_loga_error_quando_redis_indisponivel(caplog):
    """ip_bloqueado deve retornar False e logar ERROR quando Redis cai.

    Política fail-open (D-G2-1): a proteção por IP some com o Redis fora, mas o
    fail-open precisa ser visível em ERROR para alarmar a operação.

    Args:
        caplog: Fixture de captura de logs do pytest.
    """
    with patch.object(login_guard, "_get_redis", new=AsyncMock(return_value=None)):
        with caplog.at_level(logging.ERROR, logger="argus"):
            bloqueado = await login_guard.ip_bloqueado("203.0.113.7")

    assert bloqueado is False
    erros = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert erros, "fail-open de IP deveria registrar log ERROR"
    assert any("203.0.113.7" in r.getMessage() for r in erros)
