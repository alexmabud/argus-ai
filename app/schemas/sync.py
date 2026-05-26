"""Schemas Pydantic para sincronização offline.

Define estruturas de requisição e resposta para o endpoint
de sync batch que recebe itens criados offline e processa
com deduplicação por client_id.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

#: Limite por item — payload serializado em JSON. AbordagemCreate completa
#: cabe folgado em ~4KB; 64KB cobre ate' 100 pessoa_ids + observacao longa.
MAX_DADOS_BYTES = 64 * 1024
#: Limite de itens por batch. Clientes offline costumam acumular dezenas
#: entre conexoes; 100 cobre o pior caso sem virar vetor de DoS.
MAX_ITEMS_POR_BATCH = 100


class SyncItem(BaseModel):
    """Item individual de sincronização.

    Attributes:
        client_id: UUID gerado pelo cliente para deduplicação.
        tipo: Tipo do item ("abordagem", "pessoa", "veiculo"). Tipos desconhecidos
            são rejeitados em validacao.
        dados: Payload completo do item a ser criado. Rejeita > MAX_DADOS_BYTES
            apos serializacao JSON.
    """

    client_id: str = Field(..., max_length=64)
    tipo: Literal["abordagem", "pessoa", "veiculo"]
    dados: dict[str, Any]

    @field_validator("dados")
    @classmethod
    def _validar_tamanho_dados(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Aborta payloads acima de MAX_DADOS_BYTES (anti-DoS)."""
        if len(json.dumps(v, default=str)) > MAX_DADOS_BYTES:
            raise ValueError(
                f"Payload de sync excede {MAX_DADOS_BYTES // 1024} KB"
            )
        return v


class SyncBatchRequest(BaseModel):
    """Requisição de sincronização em batch.

    Attributes:
        items: Lista de itens a sincronizar (max MAX_ITEMS_POR_BATCH).
    """

    items: list[SyncItem] = Field(..., max_length=MAX_ITEMS_POR_BATCH)


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
