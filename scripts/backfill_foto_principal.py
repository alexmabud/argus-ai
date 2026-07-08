"""Recalcula Pessoa.foto_principal_url/foto_principal_thumb_url em massa.

Corrige registros que ficaram com o campo congelado numa foto errada
(ex: foto de veículo enviada por engano como tipo="rosto") de antes do
recompute automático existir (ver FotoService.recomputar_foto_principal,
chamado hoje em upload_foto/desativar). Esse script trata o passivo:
pessoas cujo foto_principal_url já estava desatualizado antes do fix
entrar em produção e que não tiveram nenhum upload/delete de foto desde
então para disparar o recompute sozinho.

Uso:
    python scripts/backfill_foto_principal.py            # dry-run, só mostra o que mudaria
    python scripts/backfill_foto_principal.py --execute  # aplica de fato
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import AsyncSessionLocal
from app.models.foto import Foto
from app.models.pessoa import Pessoa
from app.services.foto_service import FotoService


async def main(execute: bool) -> None:
    """Recalcula foto_principal_url/_thumb_url de todas as pessoas candidatas.

    Candidatas: pessoas com pelo menos uma foto tipo="rosto" ativa (podem
    precisar avançar para uma mais recente), ou pessoas com foto_principal_url
    já setada mas sem nenhuma foto de rosto ativa (precisam zerar).

    Args:
        execute: Se True, comita as alterações. Se False, mostra o diff e
            faz rollback (nada é persistido).
    """
    async with AsyncSessionLocal() as db:
        candidatas_com_rosto_ativa = select(Foto.pessoa_id).where(
            Foto.tipo == "rosto",
            Foto.ativo.is_(True),
            Foto.pessoa_id.isnot(None),
        )
        result = await db.execute(
            select(Pessoa.id).where(
                Pessoa.id.in_(candidatas_com_rosto_ativa) | Pessoa.foto_principal_url.isnot(None)
            )
        )
        pessoa_ids = [row[0] for row in result.all()]

        service = FotoService(db)
        alteradas = 0
        for pessoa_id in pessoa_ids:
            pessoa = await db.get(Pessoa, pessoa_id)
            if pessoa is None:
                continue
            antes = (pessoa.foto_principal_url, pessoa.foto_principal_thumb_url)
            await service.recomputar_foto_principal(pessoa_id)
            depois = (pessoa.foto_principal_url, pessoa.foto_principal_thumb_url)
            if antes != depois:
                alteradas += 1
                print(f"pessoa {pessoa_id}: {antes[0]!r} -> {depois[0]!r}")

        print(f"\n{len(pessoa_ids)} pessoas verificadas, {alteradas} alteradas.")
        if not execute:
            await db.rollback()
            print("Dry-run — passe --execute para aplicar de fato.")
            return

        await db.commit()
        print("Alterações commitadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Aplica de fato (sem essa flag, apenas mostra e faz rollback).",
    )
    args = parser.parse_args()
    asyncio.run(main(execute=args.execute))
