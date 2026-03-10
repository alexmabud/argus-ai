"""Schemas Pydantic para consulta unificada cross-domain.

Define estruturas para busca simultânea em pessoas, veículos e abordagens
através de um único endpoint de consulta.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.abordagem import AbordagemRead
from app.schemas.pessoa import PessoaRead
from app.schemas.veiculo import VeiculoRead


class PessoaComEnderecoRead(PessoaRead):
    """Pessoa com data de cadastro do endereço que gerou o match na busca.

    Estende PessoaRead com o campo endereco_criado_em, preenchido apenas
    quando a busca é feita por filtro de endereço (bairro/cidade/estado).
    Quando a busca é por nome/CPF, o campo fica None.

    Attributes:
        endereco_criado_em: Data de cadastro do endereço que originou o resultado.
    """

    endereco_criado_em: datetime | None = None


class VeiculoInfo(BaseModel):
    """Dados resumidos do veículo que originou o vínculo.

    Attributes:
        placa: Placa do veículo (uppercase normalizado).
        modelo: Modelo do veículo (opcional).
        cor: Cor do veículo (opcional).
        ano: Ano do veículo (opcional).
    """

    placa: str
    modelo: str | None = None
    cor: str | None = None
    ano: int | None = None

    model_config = {"from_attributes": True}


class PessoaComVeiculoRead(PessoaRead):
    """Pessoa retornada por busca de veículo com dados do vínculo.

    Estende PessoaRead com o veículo que gerou o match na busca,
    para exibir "Vinculado via: ABC·1234 · Gol Branco 2020" na ficha.

    Attributes:
        veiculo_info: Dados do veículo vinculado que originou o resultado.
    """

    veiculo_info: VeiculoInfo | None = None


class ConsultaUnificadaResponse(BaseModel):
    """Resposta da consulta unificada cross-domain.

    Retorna resultados combinados de busca em pessoas, veículos e abordagens.

    Attributes:
        pessoas: Lista de pessoas encontradas (com data de endereço quando filtrado por localidade).
        veiculos: Lista de veículos encontrados.
        abordagens: Lista de abordagens encontradas.
        total_resultados: Total de resultados combinados.
    """

    pessoas: list[PessoaComEnderecoRead] = []
    veiculos: list[VeiculoRead] = []
    abordagens: list[AbordagemRead] = []
    total_resultados: int = 0
