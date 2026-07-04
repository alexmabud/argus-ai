"""Testes unitários para PessoaVeiculoService.

Cobre criação e reativação de vínculo direto pessoa-veículo, desvínculo
(soft delete), listagem unificada (direto + via abordagem) e isolamento
multi-tenant entre guarnições.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.core.security import hash_senha
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo
from app.services.pessoa_veiculo_service import PessoaVeiculoService


class TestVincular:
    async def test_vincula_com_sucesso(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        vinculo = await service.vincular(pessoa.id, veiculo.id, usuario)
        assert vinculo.pessoa_id == pessoa.id
        assert vinculo.veiculo_id == veiculo.id
        assert vinculo.ativo is True

    async def test_vincular_duplicado_levanta_conflito(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)
        with pytest.raises(ConflitoDadosError):
            await service.vincular(pessoa.id, veiculo.id, usuario)

    async def test_vincular_pessoa_inexistente_levanta_erro(
        self, db_session: AsyncSession, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.vincular(99999, veiculo.id, usuario)

    async def test_vincular_veiculo_inexistente_levanta_erro(
        self, db_session: AsyncSession, pessoa: Pessoa, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.vincular(pessoa.id, 99999, usuario)

    async def test_vincular_pessoa_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Pessoa pertence à guarnição A; veículo também. Usuário é da B."""
        bpm_b = Bpm(nome="5o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(nome="5a Cia - GU 02", bpm_id=bpm_b.id, codigo="5BPM-5CIA-GU02")
        db_session.add(guarnicao_b)
        await db_session.flush()
        usuario_b = Usuario(
            nome="Agente Outro Tenant",
            matricula="OTHER001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(usuario_b)
        await db_session.flush()

        service = PessoaVeiculoService(db_session)
        with pytest.raises(AcessoNegadoError):
            await service.vincular(pessoa.id, veiculo.id, usuario_b)

    async def test_vincular_veiculo_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, pessoa: Pessoa, usuario: Usuario
    ):
        """Pessoa pertence à guarnição do usuário, mas o veículo é de outra."""
        bpm_b = Bpm(nome="5o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(nome="5a Cia - GU 02", bpm_id=bpm_b.id, codigo="5BPM-5CIA-GU02")
        db_session.add(guarnicao_b)
        await db_session.flush()
        veiculo_b = Veiculo(
            placa="XYZ9A88",
            modelo="Onix",
            cor="Preto",
            ano=2021,
            tipo="Carro",
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(veiculo_b)
        await db_session.flush()

        service = PessoaVeiculoService(db_session)
        with pytest.raises(AcessoNegadoError):
            await service.vincular(pessoa.id, veiculo_b.id, usuario)


class TestDesvincularEReativar:
    async def test_desvincular_e_revincular_nao_gera_conflito(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        primeiro = await service.vincular(pessoa.id, veiculo.id, usuario)

        await service.desvincular(pessoa.id, veiculo.id, usuario)

        segundo = await service.vincular(pessoa.id, veiculo.id, usuario)
        assert segundo.id == primeiro.id  # reativou a mesma linha, não criou outra
        assert segundo.ativo is True

    async def test_desvincular_inexistente_levanta_erro(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.desvincular(pessoa.id, veiculo.id, usuario)

    async def test_desvincular_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Vínculo criado pela guarnição A não pode ser desfeito por usuário da B."""
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)

        bpm_b = Bpm(nome="5o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(nome="5a Cia - GU 02", bpm_id=bpm_b.id, codigo="5BPM-5CIA-GU02")
        db_session.add(guarnicao_b)
        await db_session.flush()
        usuario_b = Usuario(
            nome="Agente Outro Tenant",
            matricula="OTHER001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(usuario_b)
        await db_session.flush()

        with pytest.raises(AcessoNegadoError):
            await service.desvincular(pessoa.id, veiculo.id, usuario_b)


class TestListarVeiculosPessoa:
    async def test_marca_origem_direto(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)

        resultado = await service.listar_veiculos_pessoa(pessoa.id, usuario)
        assert len(resultado) == 1
        assert resultado[0]["origem"] == "direto"
        assert resultado[0]["veiculo"].id == veiculo.id

    async def test_pessoa_inexistente_levanta_erro(
        self, db_session: AsyncSession, usuario: Usuario
    ):
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.listar_veiculos_pessoa(99999, usuario)

    async def test_pessoa_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, pessoa: Pessoa, usuario: Usuario
    ):
        bpm_b = Bpm(nome="5o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(nome="5a Cia - GU 02", bpm_id=bpm_b.id, codigo="5BPM-5CIA-GU02")
        db_session.add(guarnicao_b)
        await db_session.flush()
        usuario_b = Usuario(
            nome="Agente Outro Tenant",
            matricula="OTHER001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(usuario_b)
        await db_session.flush()

        service = PessoaVeiculoService(db_session)
        with pytest.raises(AcessoNegadoError):
            await service.listar_veiculos_pessoa(pessoa.id, usuario_b)
