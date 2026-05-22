"""Teste de integração: get_pessoas_por_veiculo no VeiculoRepository.

Reproduz o bug reportado: busca por placa/modelo não retorna resultados
mesmo com veículo cadastrado e vinculado a abordado via abordagem.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem, AbordagemPessoa, AbordagemVeiculo
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo
from app.repositories.veiculo_repo import VeiculoRepository


@pytest.mark.asyncio
async def test_get_pessoas_por_veiculo_por_placa_retorna_abordado(
    db_session: AsyncSession,
    guarnicao: Guarnicao,
    usuario: Usuario,
):
    """Busca por placa deve retornar abordado vinculado à abordagem.

    Cenário exato do bug: abordado tem veículo registrado numa abordagem,
    mas a busca retornava lista vazia.

    Caminho esperado:
        Pessoa → AbordagemPessoa → AbordagemVeiculo → Veiculo (placa ILIKE)
    """
    # Arrange — criar pessoa, veículo e abordagem
    pessoa = Pessoa(nome="Thiago Teste", guarnicao_id=guarnicao.id)
    veiculo = Veiculo(
        placa="PAT1E14",
        modelo="Honda CB 250F Twister",
        cor="Branca",
        ano=2016,
        guarnicao_id=guarnicao.id,
    )
    abordagem = Abordagem(
        data_hora=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usuario_id=usuario.id,
        guarnicao_id=guarnicao.id,
    )
    db_session.add_all([pessoa, veiculo, abordagem])
    await db_session.flush()

    # Vincular pessoa à abordagem (AbordagemPessoa)
    db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
    # Vincular veículo à abordagem (AbordagemVeiculo) com pessoa_id=NULL (caso legado)
    db_session.add(
        AbordagemVeiculo(
            abordagem_id=abordagem.id,
            veiculo_id=veiculo.id,
            pessoa_id=None,  # NULL — caso mais comum, o que causava 0 resultados
        )
    )
    await db_session.flush()

    repo = VeiculoRepository(db_session)

    # Act — busca por placa parcial
    resultado = await repo.get_pessoas_por_veiculo(
        placa="PAT",
        modelo=None,
        cor=None,
        guarnicao_id=guarnicao.id,
    )

    # Assert
    assert len(resultado) == 1, (
        f"Esperava 1 resultado, obteve {len(resultado)}. "
        "Bug: query não encontra abordado via AbordagemPessoa quando pessoa_id é NULL."
    )
    pessoa_retornada, veiculo_retornado = resultado[0]
    assert pessoa_retornada.nome == "Thiago Teste"
    assert veiculo_retornado.placa == "PAT1E14"


@pytest.mark.asyncio
async def test_get_pessoas_por_veiculo_por_modelo_retorna_abordado(
    db_session: AsyncSession,
    guarnicao: Guarnicao,
    usuario: Usuario,
):
    """Busca por modelo também deve retornar abordado."""
    pessoa = Pessoa(nome="Maria Modelo", guarnicao_id=guarnicao.id)
    veiculo = Veiculo(
        placa="XYZ9876",
        modelo="Twister",
        cor="Preta",
        guarnicao_id=guarnicao.id,
    )
    abordagem = Abordagem(
        data_hora=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usuario_id=usuario.id,
        guarnicao_id=guarnicao.id,
    )
    db_session.add_all([pessoa, veiculo, abordagem])
    await db_session.flush()

    db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
    db_session.add(
        AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=None)
    )
    await db_session.flush()

    repo = VeiculoRepository(db_session)
    resultado = await repo.get_pessoas_por_veiculo(
        placa=None,
        modelo="Twister",
        cor=None,
        guarnicao_id=guarnicao.id,
    )

    assert len(resultado) == 1
    assert resultado[0][0].nome == "Maria Modelo"
