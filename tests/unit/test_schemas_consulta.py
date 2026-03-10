"""Testes unitários para schemas da consulta unificada.

Valida a estrutura, validação e comportamento dos schemas de resposta
para busca de pessoas, veículos e abordagens através de consulta unificada.
"""

from datetime import UTC, datetime

from app.schemas.consulta import (
    PessoaComVeiculoRead,
    VeiculoInfo,
)


class TestVeiculoInfo:
    """Testes para o schema VeiculoInfo."""

    def test_veiculo_info_apenas_placa_obrigatoria(self):
        """Deve aceitar VeiculoInfo com apenas placa (campos opcionais em None)."""
        veiculo = VeiculoInfo(placa="ABC1234")
        assert veiculo.placa == "ABC1234"
        assert veiculo.modelo is None
        assert veiculo.cor is None
        assert veiculo.ano is None

    def test_veiculo_info_todos_campos_preenchidos(self):
        """Deve aceitar VeiculoInfo com todos os campos."""
        veiculo = VeiculoInfo(placa="ABC1234", modelo="Gol", cor="Branco", ano=2020)
        assert veiculo.placa == "ABC1234"
        assert veiculo.modelo == "Gol"
        assert veiculo.cor == "Branco"
        assert veiculo.ano == 2020

    def test_veiculo_info_model_config_from_attributes(self):
        """Deve ter model_config com from_attributes=True para SQLAlchemy."""
        assert VeiculoInfo.model_config["from_attributes"] is True


class TestPessoaComVeiculoRead:
    """Testes para o schema PessoaComVeiculoRead."""

    @staticmethod
    def _criar_pessoa_data() -> dict:
        """Cria dados básicos para instanciar PessoaRead.

        Returns:
            Dicionário com campos necessários para PessoaRead.
        """
        return {
            "id": 1,
            "nome": "João Silva",
            "guarnicao_id": 1,
            "criado_em": datetime.now(UTC),
            "atualizado_em": datetime.now(UTC),
        }

    def test_pessoa_com_veiculo_herda_campos_pessoa_read(self):
        """Deve herdar todos os campos de PessoaRead."""
        pessoa_data = self._criar_pessoa_data()
        pessoa = PessoaComVeiculoRead(**pessoa_data)

        assert pessoa.id == 1
        assert pessoa.nome == "João Silva"
        assert pessoa.guarnicao_id == 1
        assert pessoa.criado_em is not None
        assert pessoa.atualizado_em is not None

    def test_pessoa_com_veiculo_aceita_veiculo_info_preenchido(self):
        """Deve aceitar veiculo_info preenchido com dados do veículo."""
        pessoa_data = self._criar_pessoa_data()
        pessoa_data["veiculo_info"] = VeiculoInfo(
            placa="ABC1234", modelo="Gol", cor="Branco", ano=2020
        )

        pessoa = PessoaComVeiculoRead(**pessoa_data)
        assert pessoa.veiculo_info is not None
        assert pessoa.veiculo_info.placa == "ABC1234"
        assert pessoa.veiculo_info.modelo == "Gol"

    def test_pessoa_com_veiculo_aceita_veiculo_info_none(self):
        """Deve aceitar veiculo_info=None (padrão)."""
        pessoa_data = self._criar_pessoa_data()
        pessoa = PessoaComVeiculoRead(**pessoa_data)

        assert pessoa.veiculo_info is None

    def test_pessoa_com_veiculo_veiculo_info_com_dict(self):
        """Deve aceitar veiculo_info como dict e converter para VeiculoInfo."""
        pessoa_data = self._criar_pessoa_data()
        pessoa_data["veiculo_info"] = {
            "placa": "XYZ9999",
            "modelo": "Civic",
            "cor": "Preto",
            "ano": 2019,
        }

        pessoa = PessoaComVeiculoRead(**pessoa_data)
        assert isinstance(pessoa.veiculo_info, VeiculoInfo)
        assert pessoa.veiculo_info.placa == "XYZ9999"
        assert pessoa.veiculo_info.modelo == "Civic"

    def test_pessoa_com_veiculo_model_config_from_attributes(self):
        """Deve herdar model_config com from_attributes=True."""
        # PessoaComVeiculoRead herda de PessoaRead que tem o config
        assert PessoaComVeiculoRead.model_config["from_attributes"] is True
