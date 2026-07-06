"""Testes da lógica de backfill de guarnicao_id em fotos legadas.

Carrega o SQL da migration ``d10f90d496ce_backfill_guarnicao_id_em_fotos_legadas``
diretamente do arquivo (o diretório alembic/versions/ não é um pacote Python
importável normalmente) e o executa contra o banco de testes, validando a
ordem de prioridade pessoa -> abordagem -> veiculo e a idempotência (só
atualiza linhas com guarnicao_id IS NULL).
"""

import importlib.util
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.models.foto import Foto
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.veiculo import Veiculo

_MIGRATION_PATH = (
    Path(__file__).parent.parent.parent
    / "alembic"
    / "versions"
    / "d10f90d496ce_backfill_guarnicao_id_em_fotos_legadas.py"
)


def _carregar_sql_da_migration() -> str:
    """Importa o módulo da migration a partir do caminho do arquivo.

    Evita depender de um contexto de execução do Alembic (``op``) para
    testar a lógica de backfill — extrai apenas a constante de SQL.

    Returns:
        String SQL usada pela migration em ``upgrade()``.
    """
    spec = importlib.util.spec_from_file_location(
        "migration_backfill_guarnicao_id_fotos", _MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL_GUARNICAO_ID_SQL


async def _rodar_backfill(db_session: AsyncSession) -> None:
    """Executa o SQL de backfill contra a sessão de teste.

    Args:
        db_session: Sessão do banco de testes.
    """
    await db_session.execute(text(_carregar_sql_da_migration()))
    await db_session.flush()


async def _recarregar(db_session: AsyncSession, foto_id: int) -> Foto:
    """Recarrega a Foto do banco após o backfill (bypassa raw SQL na identity map).

    Args:
        db_session: Sessão do banco de testes.
        foto_id: ID da foto a recarregar.

    Returns:
        Foto com os valores atuais do banco.
    """
    foto = await db_session.get(Foto, foto_id)
    assert foto is not None
    await db_session.refresh(foto)
    return foto


class TestBackfillGuarnicaoIdFotos:
    """Testes da migration de backfill de guarnicao_id em fotos."""

    async def test_backfill_a_partir_da_pessoa(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa
    ):
        """Foto vinculada a pessoa deve herdar o guarnicao_id da pessoa."""
        foto = Foto(
            arquivo_url="/storage/argus/fotos/legado.jpg",
            tipo="rosto",
            data_hora=datetime.now(),
            pessoa_id=pessoa.id,
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id == guarnicao.id

    async def test_backfill_a_partir_da_abordagem_quando_sem_pessoa(
        self, db_session: AsyncSession, guarnicao: Guarnicao, abordagem: Abordagem
    ):
        """Foto sem pessoa mas vinculada a abordagem herda guarnicao_id da abordagem."""
        foto = Foto(
            arquivo_url="/storage/argus/fotos/legado_abordagem.jpg",
            tipo="midia_abordagem",
            data_hora=datetime.now(),
            pessoa_id=None,
            abordagem_id=abordagem.id,
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id == guarnicao.id

    async def test_backfill_a_partir_do_veiculo_quando_sem_pessoa_e_abordagem(
        self, db_session: AsyncSession, guarnicao: Guarnicao, veiculo: Veiculo
    ):
        """Foto vinculada apenas a veículo herda guarnicao_id do veículo."""
        foto = Foto(
            arquivo_url="/storage/argus/fotos/legado_veiculo.jpg",
            tipo="veiculo",
            data_hora=datetime.now(),
            pessoa_id=None,
            abordagem_id=None,
            veiculo_id=veiculo.id,
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id == guarnicao.id

    async def test_prioridade_pessoa_antes_de_abordagem(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, abordagem: Abordagem
    ):
        """Quando pessoa_id e abordagem_id estão setados, pessoa tem prioridade."""
        outra_guarnicao = Guarnicao(
            nome="Outra Guarnição", bpm_id=guarnicao.bpm_id, codigo="OUTRA-GU"
        )
        db_session.add(outra_guarnicao)
        await db_session.flush()

        # Move a abordagem para uma guarnição diferente da pessoa, para o
        # teste distinguir qual das duas foi de fato usada no backfill.
        abordagem.guarnicao_id = outra_guarnicao.id
        await db_session.flush()

        foto = Foto(
            arquivo_url="/storage/argus/fotos/legado_prioridade.jpg",
            tipo="rosto",
            data_hora=datetime.now(),
            pessoa_id=pessoa.id,
            abordagem_id=abordagem.id,
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id == pessoa.guarnicao_id
        assert atualizada.guarnicao_id != outra_guarnicao.id

    async def test_nao_sobrescreve_guarnicao_id_ja_preenchido(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa
    ):
        """Fotos que já têm guarnicao_id preenchido não são alteradas (idempotência)."""
        outra_guarnicao = Guarnicao(
            nome="Guarnição Já Correta", bpm_id=guarnicao.bpm_id, codigo="JA-CORRETA"
        )
        db_session.add(outra_guarnicao)
        await db_session.flush()

        foto = Foto(
            arquivo_url="/storage/argus/fotos/ja_preenchida.jpg",
            tipo="rosto",
            data_hora=datetime.now(),
            pessoa_id=pessoa.id,
            guarnicao_id=outra_guarnicao.id,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        # Mantém o valor original mesmo divergindo da pessoa vinculada
        assert atualizada.guarnicao_id == outra_guarnicao.id

    async def test_backfill_rodando_duas_vezes_e_seguro(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa
    ):
        """Rodar o backfill duas vezes não altera o resultado (idempotência)."""
        foto = Foto(
            arquivo_url="/storage/argus/fotos/legado_dupla_execucao.jpg",
            tipo="rosto",
            data_hora=datetime.now(),
            pessoa_id=pessoa.id,
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)
        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id == guarnicao.id

    async def test_sem_entidade_vinculada_mantem_null(self, db_session: AsyncSession):
        """Foto sem pessoa/abordagem/veiculo permanece com guarnicao_id NULL."""
        foto = Foto(
            arquivo_url="/storage/argus/fotos/orfa.jpg",
            tipo="rosto",
            data_hora=datetime.now(),
            guarnicao_id=None,
        )
        db_session.add(foto)
        await db_session.flush()

        await _rodar_backfill(db_session)

        atualizada = await _recarregar(db_session, foto.id)
        assert atualizada.guarnicao_id is None
