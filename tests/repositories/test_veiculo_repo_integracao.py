"""Teste de integração: get_pessoas_por_veiculo no VeiculoRepository.

Reproduz o bug reportado: busca por placa/modelo não retorna resultados
mesmo com veículo cadastrado e vinculado a abordado via abordagem.
"""

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem, AbordagemPessoa, AbordagemVeiculo
from app.models.bpm import Bpm
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
        data_hora=datetime.datetime.now(datetime.UTC),
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
        data_hora=datetime.datetime.now(datetime.UTC),
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


@pytest.mark.asyncio
async def test_pessoa_global_aparece_na_busca_por_veiculo(
    db_session: AsyncSession,
    guarnicao: Guarnicao,
    usuario: Usuario,
):
    """Regressão: pessoa sem guarnicao_id (global) deve aparecer na busca por veículo.

    Spec: 'Pessoas são sempre globais' — a busca por veículo NÃO deve filtrar
    pessoas por guarnicao_id. Antes do fix, Pessoa.guarnicao_id == guarnicao_id
    excluía pessoas com guarnicao_id=NULL, retornando lista vazia.
    """
    # Pessoa GLOBAL — sem guarnicao_id (caso comum criado via admin ou
    # em contexto sem guarnicao atribuída)
    pessoa = Pessoa(nome="Thiago Global", guarnicao_id=None)
    veiculo = Veiculo(
        placa="PAT1E14",
        modelo="Honda CB 250F Twister",
        cor="Branca",
        ano=2016,
        guarnicao_id=guarnicao.id,
    )
    abordagem = Abordagem(
        data_hora=datetime.datetime.now(datetime.UTC),
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
        placa="PAT",
        modelo=None,
        cor=None,
        guarnicao_id=guarnicao.id,
    )

    assert len(resultado) == 1, (
        f"Esperava 1 resultado mas obteve {len(resultado)}. "
        "Regressão: pessoa global (guarnicao_id=None) deve aparecer na busca por veículo."
    )
    assert resultado[0][0].nome == "Thiago Global"
    assert resultado[0][1].placa == "PAT1E14"


@pytest.mark.asyncio
async def test_veiculo_de_outra_guarnicao_aparece_na_busca_global(
    db_session: AsyncSession,
    guarnicao: Guarnicao,
    usuario: Usuario,
):
    """Regressão: consulta IA é global — veículo de qualquer equipe deve aparecer.

    Ao passar guarnicao_id=None no repo, o filtro Veiculo.guarnicao_id
    não é aplicado, tornando a busca cross-tenant para a consulta IA.
    """
    # Segunda guarnição — outro tenant
    bpm = Bpm(nome="BPM Teste Cross")
    db_session.add(bpm)
    await db_session.flush()
    outra_guarnicao = Guarnicao(nome="Outra Equipe", bpm_id=bpm.id, codigo="OUTRA-001")
    db_session.add(outra_guarnicao)
    await db_session.flush()

    # Pessoa e veículo pertencem à OUTRA equipe
    pessoa = Pessoa(nome="Carlos Outra Equipe", guarnicao_id=outra_guarnicao.id)
    veiculo = Veiculo(
        placa="ABC1234",
        modelo="Corolla",
        guarnicao_id=outra_guarnicao.id,
    )
    abordagem = Abordagem(
        data_hora=datetime.datetime.now(datetime.UTC),
        usuario_id=usuario.id,
        guarnicao_id=outra_guarnicao.id,
    )
    db_session.add_all([pessoa, veiculo, abordagem])
    await db_session.flush()

    db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
    db_session.add(
        AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=None)
    )
    await db_session.flush()

    repo = VeiculoRepository(db_session)

    # guarnicao_id=None → busca global (qualquer usuário, qualquer equipe)
    resultado = await repo.get_pessoas_por_veiculo(
        placa="ABC",
        modelo=None,
        cor=None,
        guarnicao_id=None,
    )

    assert len(resultado) == 1, (
        f"Esperava 1 resultado mas obteve {len(resultado)}. "
        "Consulta IA deve ser global (guarnicao_id=None)."
    )
    assert resultado[0][0].nome == "Carlos Outra Equipe"
