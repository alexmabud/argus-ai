"""Testes do schema SyncBatchRequest contra payloads adversariais.

Garante que atacante autenticado nao consiga DoS ou crash via payload
malformado (batch enorme, dados gigantes, tipo invalido).
"""

import pytest
from pydantic import ValidationError

from app.schemas.sync import MAX_DADOS_BYTES, MAX_ITEMS_POR_BATCH, SyncBatchRequest


def _item(tipo: str = "abordagem", client_id: str = "abc", dados: dict | None = None) -> dict:
    return {"tipo": tipo, "client_id": client_id, "dados": dados or {}}


def test_sync_rejeita_tipo_desconhecido():
    """tipo fora do whitelist deve falhar em validacao (antes era passado adiante)."""
    with pytest.raises(ValidationError):
        SyncBatchRequest(items=[_item(tipo="malicioso")])


def test_sync_rejeita_batch_grande_demais():
    """Mais de MAX_ITEMS_POR_BATCH itens deve ser rejeitado."""
    items = [_item(client_id=f"x{i}") for i in range(MAX_ITEMS_POR_BATCH + 1)]
    with pytest.raises(ValidationError):
        SyncBatchRequest(items=items)


def test_sync_rejeita_dados_acima_do_limite():
    """dados serializado > MAX_DADOS_BYTES deve ser rejeitado (anti-DoS)."""
    enorme = {"observacao": "x" * (MAX_DADOS_BYTES + 100)}
    with pytest.raises(ValidationError, match="excede"):
        SyncBatchRequest(items=[_item(dados=enorme)])


def test_sync_rejeita_client_id_muito_longo():
    """client_id > 64 chars deve ser rejeitado."""
    with pytest.raises(ValidationError):
        SyncBatchRequest(items=[_item(client_id="a" * 200)])


def test_sync_aceita_payload_legitimo():
    """Payload tipico de abordagem offline deve continuar passando."""
    dados = {
        "data_hora": "2026-05-26T12:00:00+00:00",
        "latitude": -8.05,
        "longitude": -34.9,
        "origem": "offline",
        "pessoa_ids": [1, 2],
        "veiculo_ids": [],
    }
    req = SyncBatchRequest(items=[_item(dados=dados)])
    assert len(req.items) == 1
    assert req.items[0].tipo == "abordagem"
