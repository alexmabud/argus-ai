"""Testes unitários para PessoaVeiculoService.

Cobre criação e reativação de vínculo direto pessoa-veículo, desvínculo
(soft delete), listagem unificada (direto + via abordagem) e isolamento
multi-tenant entre guarnições.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.core.security import hash_senha
from app.models.abordagem import Abordagem, AbordagemPessoa, AbordagemVeiculo
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
        """Cria vínculo direto novo entre pessoa e veículo, ativo desde já."""
        service = PessoaVeiculoService(db_session)
        vinculo = await service.vincular(pessoa.id, veiculo.id, usuario)
        assert vinculo.pessoa_id == pessoa.id
        assert vinculo.veiculo_id == veiculo.id
        assert vinculo.ativo is True

    async def test_vinculo_veiculo_acessivel_sem_veiculo_pre_carregado_na_sessao(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Regressão: vinculo.veiculo deve ser acessível sem MissingGreenlet.

        Em produção, cada requisição usa uma sessão nova — o Veiculo nunca
        esteve no identity map antes de vincular() carregá-lo. Nos testes,
        a fixture `veiculo` e o service compartilham a MESMA sessão (padrão
        de `tests/conftest.py::client`), o que mascarava esse bug: o objeto
        já estava resolvido antes mesmo do service tocar nele. `expunge()`
        remove o veiculo do identity map da sessão de teste antes de
        vincular(), reproduzindo a condição real de uma requisição nova —
        sem isso, este teste passaria mesmo com o bug presente (já
        confirmado manualmente: reproduz MissingGreenlet real via reversão
        temporária do fix, e via HTTP direto contra um uvicorn real).
        """
        db_session.expunge(veiculo)
        service = PessoaVeiculoService(db_session)
        vinculo = await service.vincular(pessoa.id, veiculo.id, usuario)

        # A linha abaixo é o próprio teste: acessar .veiculo é exatamente o
        # que app/api/v1/pessoas.py faz para montar a resposta da rota
        # POST /pessoas/{id}/veiculos/{id} — sem o fix, levanta MissingGreenlet.
        veiculo_relacionado = vinculo.veiculo
        assert veiculo_relacionado is not None
        assert veiculo_relacionado.id == veiculo.id

    async def test_vincular_duplicado_levanta_conflito(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Vincular o mesmo par duas vezes (ambas ativas) levanta ConflitoDadosError."""
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)
        with pytest.raises(ConflitoDadosError):
            await service.vincular(pessoa.id, veiculo.id, usuario)

    async def test_vincular_pessoa_inexistente_levanta_erro(
        self, db_session: AsyncSession, veiculo: Veiculo, usuario: Usuario
    ):
        """Pessoa com ID inexistente levanta NaoEncontradoError."""
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.vincular(99999, veiculo.id, usuario)

    async def test_vincular_veiculo_inexistente_levanta_erro(
        self, db_session: AsyncSession, pessoa: Pessoa, usuario: Usuario
    ):
        """Veículo com ID inexistente levanta NaoEncontradoError."""
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.vincular(pessoa.id, 99999, usuario)

    async def test_vincular_corrida_no_insert_gera_conflito_dados(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        usuario: Usuario,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Corrida entre duas requisições vinculando o mesmo par pela 1a vez.

        Simula o cenário em que get_par (include_inactive=True) não
        encontra nenhuma linha para o par — porque ainda não existia no
        momento da leitura desta requisição — mas o vínculo já foi
        criado por outra requisição concorrente antes do INSERT desta.
        O banco rejeita o INSERT duplicado (unique constraint) e o
        service deve converter isso em ConflitoDadosError, não deixar o
        IntegrityError vazar como erro 500.
        """
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)

        async def get_par_desatualizado(*args, **kwargs):
            return None

        monkeypatch.setattr(service.repo, "get_par", get_par_desatualizado)

        with pytest.raises(ConflitoDadosError):
            await service.vincular(pessoa.id, veiculo.id, usuario)

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
        """Desvincular e vincular de novo o mesmo par reativa a linha, sem 409."""
        service = PessoaVeiculoService(db_session)
        primeiro = await service.vincular(pessoa.id, veiculo.id, usuario)

        await service.desvincular(pessoa.id, veiculo.id, usuario)

        segundo = await service.vincular(pessoa.id, veiculo.id, usuario)
        assert segundo.id == primeiro.id  # reativou a mesma linha, não criou outra
        assert segundo.ativo is True

    async def test_reativar_reseta_campos_de_desativacao(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Reativar um vínculo soft-deleted zera desativado_em/desativado_por_id."""
        service = PessoaVeiculoService(db_session)
        primeiro = await service.vincular(pessoa.id, veiculo.id, usuario)
        await service.desvincular(pessoa.id, veiculo.id, usuario)
        await db_session.refresh(primeiro)
        assert primeiro.ativo is False
        assert primeiro.desativado_em is not None
        assert primeiro.desativado_por_id == usuario.id

        segundo = await service.vincular(pessoa.id, veiculo.id, usuario)
        assert segundo.desativado_em is None
        assert segundo.desativado_por_id is None
        assert segundo.criado_por_id == usuario.id

    async def test_desvincular_inexistente_levanta_erro(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Desvincular um par que nunca foi vinculado levanta NaoEncontradoError."""
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.desvincular(pessoa.id, veiculo.id, usuario)

    async def test_desvincular_ja_desvinculado_levanta_erro(
        self, db_session: AsyncSession, pessoa: Pessoa, veiculo: Veiculo, usuario: Usuario
    ):
        """Desvincular duas vezes seguidas: a segunda chamada não encontra vínculo ativo."""
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)
        await service.desvincular(pessoa.id, veiculo.id, usuario)
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
        """Veículo vinculado só diretamente (sem abordagem) tem origem 'direto'."""
        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)

        resultado = await service.listar_veiculos_pessoa(pessoa.id, usuario)
        assert len(resultado) == 1
        assert resultado[0]["origem"] == "direto"
        assert resultado[0]["veiculo"].id == veiculo.id

    async def test_marca_origem_abordagem_quando_so_via_abordagem(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        usuario: Usuario,
        abordagem: Abordagem,
    ):
        """Veículo só vinculado via abordagem (sem vínculo direto) tem origem 'abordagem'."""
        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        db_session.add(
            AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=pessoa.id)
        )
        await db_session.flush()

        service = PessoaVeiculoService(db_session)
        resultado = await service.listar_veiculos_pessoa(pessoa.id, usuario)
        assert len(resultado) == 1
        assert resultado[0]["origem"] == "abordagem"
        assert resultado[0]["veiculo"].id == veiculo.id

    async def test_direto_prevalece_sobre_abordagem_quando_ambos(
        self,
        db_session: AsyncSession,
        pessoa: Pessoa,
        veiculo: Veiculo,
        usuario: Usuario,
        abordagem: Abordagem,
    ):
        """Veículo com vínculo direto E via abordagem aparece só uma vez, com origem 'direto'."""
        db_session.add(AbordagemPessoa(abordagem_id=abordagem.id, pessoa_id=pessoa.id))
        db_session.add(
            AbordagemVeiculo(abordagem_id=abordagem.id, veiculo_id=veiculo.id, pessoa_id=pessoa.id)
        )
        await db_session.flush()

        service = PessoaVeiculoService(db_session)
        await service.vincular(pessoa.id, veiculo.id, usuario)

        resultado = await service.listar_veiculos_pessoa(pessoa.id, usuario)
        assert len(resultado) == 1
        assert resultado[0]["origem"] == "direto"
        assert resultado[0]["veiculo"].id == veiculo.id

    async def test_pessoa_inexistente_levanta_erro(
        self, db_session: AsyncSession, usuario: Usuario
    ):
        """Pessoa com ID inexistente levanta NaoEncontradoError."""
        service = PessoaVeiculoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.listar_veiculos_pessoa(99999, usuario)

    async def test_pessoa_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, pessoa: Pessoa, usuario: Usuario
    ):
        """Listar veículos de pessoa de outra guarnição levanta AcessoNegadoError."""
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
