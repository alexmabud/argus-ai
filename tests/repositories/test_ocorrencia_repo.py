"""Testes do repositório de ocorrências.

Verifica comportamentos específicos do OcorrenciaRepository,
como ordenação e buscas especializadas.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao
from app.models.ocorrencia import Ocorrencia
from app.models.usuario import Usuario
from app.repositories.ocorrencia_repo import OcorrenciaRepository


@pytest.mark.asyncio
async def test_listar_ordenado_por_data_ocorrencia(
    db_session: AsyncSession,
    guarnicao: Guarnicao,
    usuario: Usuario,
):
    """Verifica que get_all() retorna ocorrências ordenadas por data_ocorrencia DESC."""
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    anteontem = hoje - timedelta(days=2)

    repo = OcorrenciaRepository(db_session)

    # Criar ocorrências fora de ordem
    for i, data in enumerate([ontem, hoje, anteontem]):
        oc = Ocorrencia(
            numero_ocorrencia=f"TEST-{i:04d}",
            arquivo_pdf_url="http://example.com/test.pdf",
            data_ocorrencia=data,
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(oc)
    await db_session.commit()

    resultado = await repo.get_all(guarnicao_id=guarnicao.id)

    datas = [oc.data_ocorrencia for oc in resultado]
    assert datas == sorted(datas, reverse=True), "Deve estar ordenado por data_ocorrencia DESC"
