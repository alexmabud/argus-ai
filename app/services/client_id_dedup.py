"""Helper compartilhado de deduplicação por client_id no cadastro offline.

Sync offline pode reenviar o mesmo registro (retry de rede, reconexão) —
`client_id` (gerado no cliente) identifica esse registro de forma estável
entre tentativas. `criar_com_retry_client_id` centraliza o tratamento de
corrida entre o dedup-check e o insert, usado por PessoaService e
VeiculoService (mesmo padrão antes duplicado nos dois — achado de revisão
pós-#18/2026-07-13).
"""

from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base
from app.repositories.base import BaseRepository

T = TypeVar("T", bound=Base)


async def criar_com_retry_client_id(
    db: AsyncSession,
    repo: BaseRepository[T],
    entidade: T,
    client_id: str | None,
    erro_conflito: Exception,
) -> tuple[T, bool]:
    """Insere a entidade, recuperando-se de uma corrida de client_id concorrente.

    Assume que o chamador já fez o dedup-check inicial (`repo.get_by_client_id`)
    antes de construir `entidade` — este helper só cobre a janela de corrida
    entre esse check e o insert: se outra requisição concorrente inseriu o
    MESMO client_id nesse meio-tempo, o índice único parcial rejeita o
    segundo insert com IntegrityError. Faz rollback (necessário para liberar
    a transação abortada antes de re-consultar) e retorna a entidade
    vencedora da corrida em vez de duplicar — mantém a idempotência do sync
    offline sob concorrência.

    Args:
        db: Sessão assíncrona do SQLAlchemy (para rollback em caso de corrida).
        repo: Repositório da entidade (precisa de `create` e `get_by_client_id`).
        entidade: Instância já construída, pronta para inserir.
        client_id: client_id da entidade, ou None se não informado (sync
            direto, não offline — nesse caso não há o que recuperar na corrida).
        erro_conflito: Exceção a levantar se o IntegrityError não for uma
            corrida de client_id recuperável (ex.: violação de unicidade de
            outro campo, como CPF ou placa).

    Returns:
        Tupla (entidade, foi_criada). `foi_criada=False` quando uma corrida
        concorrente venceu o insert e a entidade retornada é a já existente —
        o `rollback()` desfaz TUDO que a sessão tinha pendente (não só este
        insert), então o chamador não deve tratar essa entidade como recém-
        criada (ex.: pular log de auditoria de CREATE — não houve create).

    Raises:
        Exception: `erro_conflito`, se o IntegrityError não for recuperável
            via client_id.
    """
    try:
        await repo.create(entidade)
    except IntegrityError:
        await db.rollback()
        if client_id:
            existing = await repo.get_by_client_id(client_id)
            if existing:
                return existing, False
        raise erro_conflito from None
    return entidade, True
