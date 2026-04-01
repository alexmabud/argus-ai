"""Migra endereços em texto para a tabela de localidades hierárquicas.

Lê todos os registros de enderecos_pessoa que possuem cidade/bairro
em texto mas ainda não têm cidade_id/bairro_id preenchidos. Para cada
registro, localiza ou cria a entrada correspondente em localidades e
atualiza os campos FK no endereço.

Uso:
    python scripts/migrar_localidades_texto.py [--dry-run]

Flags:
    --dry-run   Exibe o que seria migrado sem gravar nada no banco.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import unicodedata
from argparse import ArgumentParser

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.endereco import EnderecoPessoa
from app.models.localidade import Localidade

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrar_localidades")


def _normalizar(nome: str) -> str:
    """Normaliza texto para busca: remove acentos e converte para minúsculas.

    Args:
        nome: Texto original.

    Returns:
        Texto sem acentos em minúsculas.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", nome.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


async def _get_or_create_localidade(
    session: AsyncSession,
    nome: str,
    tipo: str,
    parent_id: int,
    dry_run: bool,
    cache: dict,
) -> int | None:
    """Busca ou cria uma localidade pelo nome normalizado e parent_id.

    Args:
        session: Sessão assíncrona do banco.
        nome: Nome original da localidade.
        tipo: Tipo — 'cidade' ou 'bairro'.
        parent_id: ID do pai (estado para cidade, cidade para bairro).
        dry_run: Se True, não cria registros.
        cache: Dicionário local para evitar queries repetidas.

    Returns:
        ID da localidade encontrada ou criada, ou None em dry_run.
    """
    nome_norm = _normalizar(nome)
    chave = (tipo, parent_id, nome_norm)

    if chave in cache:
        return cache[chave]

    result = await session.execute(
        select(Localidade).where(
            Localidade.tipo == tipo,
            Localidade.parent_id == parent_id,
            Localidade.nome == nome_norm,
            Localidade.ativo.is_(True),
        )
    )
    localidade = result.scalar_one_or_none()

    if localidade:
        cache[chave] = localidade.id
        return localidade.id

    if dry_run:
        logger.info("[DRY-RUN] Criaria %s: '%s' (parent_id=%d)", tipo, nome, parent_id)
        cache[chave] = None
        return None

    nova = Localidade(
        nome=nome_norm,
        nome_exibicao=nome.strip(),
        tipo=tipo,
        parent_id=parent_id,
    )
    session.add(nova)
    await session.flush()
    cache[chave] = nova.id
    logger.info("Criado %s: '%s' (id=%d, parent_id=%d)", tipo, nome, nova.id, parent_id)
    return nova.id


async def migrar(session: AsyncSession, dry_run: bool) -> None:
    """Executa a migração de endereços texto → localidades FK.

    Processa apenas endereços ativos onde cidade ou bairro em texto
    estão preenchidos mas os campos FK ainda são nulos.

    Args:
        session: Sessão assíncrona do banco.
        dry_run: Se True, apenas loga sem gravar.
    """
    # Buscar todos os estados para montar mapa sigla → id
    estados_result = await session.execute(
        select(Localidade).where(Localidade.tipo == "estado", Localidade.ativo.is_(True))
    )
    estados = {e.sigla: e.id for e in estados_result.scalars().all() if e.sigla}
    logger.info("Estados carregados: %d", len(estados))

    # Buscar endereços com texto mas sem FK de cidade ou bairro
    enderecos_result = await session.execute(
        select(EnderecoPessoa).where(
            EnderecoPessoa.ativo.is_(True),
            (EnderecoPessoa.cidade.isnot(None)) | (EnderecoPessoa.bairro.isnot(None)),
            (EnderecoPessoa.cidade_id.is_(None)) | (EnderecoPessoa.bairro_id.is_(None)),
        )
    )
    enderecos = enderecos_result.scalars().all()
    logger.info("Endereços a processar: %d", len(enderecos))

    cache: dict = {}
    migrados = 0
    ignorados = 0

    for end in enderecos:
        # Resolver estado_id a partir da sigla em texto
        estado_id = end.estado_id
        if estado_id is None and end.estado:
            estado_id = estados.get(end.estado.upper())
            if estado_id is None:
                logger.warning(
                    "Estado '%s' não encontrado — endereco_id=%d ignorado",
                    end.estado,
                    end.id,
                )
                ignorados += 1
                continue

        if estado_id is None:
            logger.warning(
                "Endereço id=%d sem estado — não é possível criar cidade/bairro",
                end.id,
            )
            ignorados += 1
            continue

        cidade_id = end.cidade_id
        if cidade_id is None and end.cidade and end.cidade.strip():
            cidade_id = await _get_or_create_localidade(
                session=session,
                nome=end.cidade.strip(),
                tipo="cidade",
                parent_id=estado_id,
                dry_run=dry_run,
                cache=cache,
            )

        bairro_id = end.bairro_id
        if bairro_id is None and end.bairro and end.bairro.strip() and cidade_id:
            bairro_id = await _get_or_create_localidade(
                session=session,
                nome=end.bairro.strip(),
                tipo="bairro",
                parent_id=cidade_id,
                dry_run=dry_run,
                cache=cache,
            )

        if dry_run:
            logger.info(
                "[DRY-RUN] endereco_id=%d: estado_id=%s cidade_id=%s bairro_id=%s",
                end.id,
                estado_id,
                cidade_id,
                bairro_id,
            )
            migrados += 1
            continue

        await session.execute(
            update(EnderecoPessoa)
            .where(EnderecoPessoa.id == end.id)
            .values(
                estado_id=estado_id,
                cidade_id=cidade_id,
                bairro_id=bairro_id,
            )
        )
        migrados += 1

    if not dry_run:
        await session.commit()

    logger.info(
        "Concluído — migrados: %d | ignorados: %d%s",
        migrados,
        ignorados,
        " (dry-run, nada gravado)" if dry_run else "",
    )


async def main(dry_run: bool) -> None:
    """Ponto de entrada do script.

    Args:
        dry_run: Se True, executa sem gravar.
    """
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        await migrar(session, dry_run=dry_run)

    await engine.dispose()


if __name__ == "__main__":
    parser = ArgumentParser(description="Migra endereços texto para localidades FK.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas loga, não grava.")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
