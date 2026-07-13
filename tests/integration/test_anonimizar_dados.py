"""Teste de integração da anonimização LGPD (``scripts/anonimizar_dados.py``).

Valida o passe vertical corrigido do issue #01 do review de segurança
(2026-07-13): ``pessoa.cpf_criptografado`` era um atributo inexistente no
modelo (o campo real é ``cpf_encrypted``), então o CPF cifrado nunca era
de fato apagado. Cobre também a extensão de escopo (nome da mãe, foto de
perfil, endereço/geolocalização) e o caminho de escrita real (não apenas
dry-run) contra um banco de teste.
"""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endereco import EnderecoPessoa
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "anonimizar_dados.py"
_spec = importlib.util.spec_from_file_location("anonimizar_dados", _SCRIPT)
anon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(anon)


async def _criar_pessoa_soft_deleted(db_session: AsyncSession, guarnicao: Guarnicao) -> Pessoa:
    """Cria uma pessoa soft-deleted há mais tempo que a retenção, com PII completa."""
    pessoa = Pessoa(
        nome="Carlos Eduardo Souza",
        apelido="Cadu",
        nome_mae="Maria Eduarda Souza",
        cpf_encrypted="gAAAAA-cifrado-fake",
        cpf_hash="a" * 64,
        observacoes="Suspeito de furto reincidente.",
        data_nascimento=datetime(1990, 5, 20, tzinfo=UTC).date(),
        foto_principal_url="/storage/argus-fotos/fotos/perfil.jpg",
        foto_principal_thumb_url="/storage/argus-fotos/fotos/perfil_thumb.jpg",
        guarnicao_id=guarnicao.id,
        ativo=False,
        desativado_em=datetime.now(UTC) - timedelta(days=3000),
    )
    db_session.add(pessoa)
    await db_session.flush()
    return pessoa


async def _criar_endereco(db_session: AsyncSession, pessoa: Pessoa) -> EnderecoPessoa:
    endereco = EnderecoPessoa(
        pessoa_id=pessoa.id,
        endereco="Rua das Flores, 123",
        bairro="Centro",
        cidade="Rio de Janeiro",
        estado="RJ",
    )
    db_session.add(endereco)
    await db_session.flush()
    return endereco


@pytest.mark.asyncio
async def test_anonimizar_pessoas_zera_cpf_encrypted_e_cpf_hash(
    db_session: AsyncSession, guarnicao: Guarnicao
):
    """Regressão do bug: cpf_encrypted (não cpf_criptografado) deve ficar NULL."""
    pessoa = await _criar_pessoa_soft_deleted(db_session, guarnicao)
    cutoff = datetime.now(UTC) - timedelta(days=1825)

    count = await anon.anonimizar_pessoas(db_session, cutoff, dry_run=False)
    await db_session.commit()

    assert count == 1
    result = await db_session.execute(select(Pessoa).where(Pessoa.id == pessoa.id))
    persisted = result.scalar_one()
    assert persisted.cpf_encrypted is None
    assert persisted.cpf_hash is None
    assert persisted.nome == "ANONIMIZADO"
    assert persisted.apelido is None
    assert persisted.nome_mae is None
    assert persisted.observacoes is None
    assert persisted.data_nascimento is None
    assert persisted.foto_principal_url is None
    assert persisted.foto_principal_thumb_url is None


@pytest.mark.asyncio
async def test_anonimizar_pessoas_dry_run_nao_escreve_no_banco(
    db_session: AsyncSession, guarnicao: Guarnicao
):
    """Dry-run não deve tocar o banco — o caminho de escrita real é testado à parte."""
    pessoa = await _criar_pessoa_soft_deleted(db_session, guarnicao)
    cutoff = datetime.now(UTC) - timedelta(days=1825)

    count = await anon.anonimizar_pessoas(db_session, cutoff, dry_run=True)
    await db_session.commit()

    assert count == 1
    result = await db_session.execute(select(Pessoa).where(Pessoa.id == pessoa.id))
    persisted = result.scalar_one()
    assert persisted.cpf_encrypted == "gAAAAA-cifrado-fake"
    assert persisted.nome == "Carlos Eduardo Souza"


@pytest.mark.asyncio
async def test_anonimizar_enderecos_remove_localizacao(
    db_session: AsyncSession, guarnicao: Guarnicao
):
    """Endereço vinculado a pessoa anonimizada perde logradouro/bairro/cidade/estado."""
    pessoa = await _criar_pessoa_soft_deleted(db_session, guarnicao)
    endereco = await _criar_endereco(db_session, pessoa)
    cutoff = datetime.now(UTC) - timedelta(days=1825)

    count = await anon.anonimizar_enderecos(db_session, cutoff, dry_run=False)
    await db_session.commit()

    assert count == 1
    stmt = select(EnderecoPessoa).where(EnderecoPessoa.id == endereco.id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one()
    assert persisted.endereco == anon._VALOR_ANONIMIZADO
    assert persisted.bairro is None
    assert persisted.cidade is None
    assert persisted.estado is None


@pytest.mark.asyncio
async def test_anonimizar_enderecos_ignora_pessoa_dentro_da_retencao(
    db_session: AsyncSession, guarnicao: Guarnicao
):
    """Endereço de pessoa desativada recentemente (dentro da retenção) não é tocado."""
    pessoa = Pessoa(
        nome="Ana Paula Lima",
        guarnicao_id=guarnicao.id,
        ativo=False,
        desativado_em=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add(pessoa)
    await db_session.flush()
    endereco = await _criar_endereco(db_session, pessoa)
    cutoff = datetime.now(UTC) - timedelta(days=1825)

    count = await anon.anonimizar_enderecos(db_session, cutoff, dry_run=False)
    await db_session.commit()

    assert count == 0
    stmt = select(EnderecoPessoa).where(EnderecoPessoa.id == endereco.id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one()
    assert persisted.endereco == "Rua das Flores, 123"
