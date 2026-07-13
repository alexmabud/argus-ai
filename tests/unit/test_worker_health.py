"""Testes da métrica argus_worker_alive por instância (achado #12/2026-07-13).

Cobre a lógica de leitura da health-check key de cada worker no Redis e a
atualização do gauge — sem depender de Redis real (client fake em memória,
mesmo padrão de tests/unit/test_login_guard.py).
"""

import asyncio
from unittest.mock import patch

import pytest

from app.config import settings
from app.core import worker_health


class _FakeRedis:
    """Redis em memória mínimo — só o suficiente para EXISTS/aclose."""

    def __init__(self, chaves_existentes: set[str]) -> None:
        self._chaves = chaves_existentes

    async def exists(self, key: str) -> int:
        return 1 if key in self._chaves else 0

    async def aclose(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _worker_ids(monkeypatch):
    """Configura WORKER_IDS para o teste e restaura depois."""
    monkeypatch.setattr(settings, "WORKER_IDS", "worker-1,worker-2")
    yield


def _valor_gauge(worker_id: str) -> float:
    return worker_health.WORKER_ALIVE_GAUGE.labels(worker_id=worker_id)._value.get()


@pytest.mark.asyncio
async def test_marca_vivo_quando_chave_fresca_no_redis():
    """Worker com health-check key presente no Redis é marcado como 1 (vivo)."""
    fake = _FakeRedis({"arq:health-check:worker-1", "arq:health-check:worker-2"})
    with patch.object(worker_health.aioredis, "from_url", return_value=fake):
        await worker_health.atualizar_worker_health_gauge()

    assert _valor_gauge("worker-1") == 1
    assert _valor_gauge("worker-2") == 1


@pytest.mark.asyncio
async def test_marca_morto_quando_chave_ausente():
    """Worker sem health-check key (expirada/nunca escrita) é marcado como 0."""
    fake = _FakeRedis({"arq:health-check:worker-1"})  # worker-2 ausente
    with patch.object(worker_health.aioredis, "from_url", return_value=fake):
        await worker_health.atualizar_worker_health_gauge()

    assert _valor_gauge("worker-1") == 1
    assert _valor_gauge("worker-2") == 0


@pytest.mark.asyncio
async def test_sem_worker_ids_configurado_nao_faz_nada(monkeypatch):
    """WORKER_IDS vazio (dev/single-worker) não deve tentar consultar o Redis."""
    monkeypatch.setattr(settings, "WORKER_IDS", "")
    with patch.object(worker_health.aioredis, "from_url") as mock_from_url:
        await worker_health.atualizar_worker_health_gauge()

    mock_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_falha_de_conexao_marca_todos_workers_como_zero():
    """Redis indisponível não deve deixar o gauge "vivo" por omissão — marca 0."""
    worker_health.WORKER_ALIVE_GAUGE.labels(worker_id="worker-1").set(1)

    with patch.object(worker_health.aioredis, "from_url", side_effect=ConnectionError("down")):
        await worker_health.atualizar_worker_health_gauge()

    assert _valor_gauge("worker-1") == 0
    assert _valor_gauge("worker-2") == 0


@pytest.mark.asyncio
async def test_loop_worker_health_atualiza_e_repete(monkeypatch):
    """O loop chama atualizar_worker_health_gauge repetidamente até ser cancelado."""
    chamadas = 0

    async def _fake_atualizar():
        nonlocal chamadas
        chamadas += 1
        if chamadas >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(worker_health, "atualizar_worker_health_gauge", _fake_atualizar)

    with pytest.raises(asyncio.CancelledError):
        await worker_health.loop_worker_health(intervalo_segundos=0)

    assert chamadas == 2
