"""Teste de similaridade facial via pgvector (FotoRepository).

Exercita a busca por similaridade (operador cosseno do pgvector) com embeddings
512-dim sintéticos — sem depender do modelo InsightFace. Antes a suíte de fotos
só cobria 401 e nunca exercia a similaridade pgvector (achado #3 do Grupo 9).
"""

from datetime import datetime

import pytest

from app.models.foto import Foto
from app.repositories.foto_repo import FotoRepository


@pytest.mark.asyncio
async def test_busca_similaridade_facial_filtra_por_threshold(db_session, pessoa):
    """Retorna o rosto próximo (cosseno alto) e exclui o ortogonal (< threshold).

    Args:
        db_session: Sessão do banco de testes.
        pessoa: Fixture de pessoa (dona das fotos).
    """
    repo = FotoRepository(db_session)

    rosto_a = [1.0] + [0.0] * 511  # embedding do "rosto A"
    ortogonal = [0.0, 1.0] + [0.0] * 510  # cosseno ~0 com A → abaixo do threshold
    consulta = [0.99] + [0.01] * 511  # quase igual a A

    db_session.add_all(
        [
            Foto(
                arquivo_url="/storage/b/rosto_a.jpg",
                tipo="rosto",
                data_hora=datetime.now(),
                pessoa_id=pessoa.id,
                embedding_face=rosto_a,
                face_processada=True,
            ),
            Foto(
                arquivo_url="/storage/b/ortogonal.jpg",
                tipo="rosto",
                data_hora=datetime.now(),
                pessoa_id=pessoa.id,
                embedding_face=ortogonal,
                face_processada=True,
            ),
        ]
    )
    await db_session.flush()

    resultados = await repo.buscar_por_similaridade_facial(consulta, top_k=5, threshold=0.6)

    # Só o rosto A passa o threshold de 0.6; o ortogonal (cosseno ~0) é excluído.
    assert len(resultados) == 1
    foto, similaridade = resultados[0]
    assert foto.arquivo_url == "/storage/b/rosto_a.jpg"
    assert similaridade >= 0.6
