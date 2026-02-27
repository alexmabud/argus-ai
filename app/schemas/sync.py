"""Schemas Pydantic para sincronização offline.

Define estruturas de requisição e resposta para o endpoint
de sync batch que recebe itens criados offline e processa
com deduplicação por client_id.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SyncItem(BaseModel):
    """Item individual de sincronização.

    Attributes:
        client_id: UUID gerado pelo cliente para deduplicação.
        tipo: Tipo do item ("abordagem", "pessoa", "veiculo").
        dados: Payload completo do item a ser criado.
    """

    client_id: str
    tipo: str
    dados: dict[str, Any]


class SyncBatchRequest(BaseModel):
    """Requisição de sincronização em batch.

    Attributes:
        items: Lista de itens a sincronizar.
    """

    items: list[SyncItem]


class SyncItemResult(BaseModel):
    """Resultado de sincronização de um item.

    Attributes:
        client_id: UUID do item processado.
        status: Resultado ("ok" ou "error").
        error: Mensagem de erro se status="error".
    """

    client_id: str
    status: str
    error: str | None = None


class SyncBatchResponse(BaseModel):
    """Resposta de sincronização em batch.

    Attributes:
        results: Lista de resultados por item.
    """

    results: list[SyncItemResult]
