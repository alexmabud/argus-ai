"""Enfileira backfill de thumbnails para todas as fotos sem thumb.

Procura por ``Foto.thumbnail_url IS NULL`` (apenas registros ``ativo=True``)
e enfileira ``gerar_thumbnail_backfill_task`` no arq worker para cada uma.

Uso:
    python scripts/backfill_thumbnails.py            # dry-run, só conta
    python scripts/backfill_thumbnails.py --execute  # enfileira de fato
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import AsyncSessionLocal
from app.models.foto import Foto


async def main(execute: bool) -> None:
    """Lista (ou enfileira) backfill de thumbnails para fotos sem thumb.

    Args:
        execute: Se True, enfileira jobs no arq. Se False, apenas conta.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Foto.id).where(
                Foto.thumbnail_url.is_(None),
                Foto.ativo.is_(True),
            )
        )
        ids = [row[0] for row in result.all()]

    print(f"{len(ids)} fotos sem thumbnail.")
    if not execute:
        print("Dry-run — passe --execute para enfileirar.")
        return

    from arq.connections import create_pool

    from app.worker import WorkerSettings

    pool = await create_pool(WorkerSettings.redis_settings)
    try:
        for foto_id in ids:
            await pool.enqueue_job("gerar_thumbnail_backfill_task", foto_id)
    finally:
        await pool.aclose()
    print(f"{len(ids)} jobs enfileirados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Enfileira de fato (sem essa flag, apenas conta).",
    )
    args = parser.parse_args()
    asyncio.run(main(execute=args.execute))
