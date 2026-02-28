"""Schemas Pydantic para CRUD de Abordagem.

Define estruturas de requisição e resposta para criação, atualização,
leitura e busca de abordagens em campo, incluindo vinculação com
pessoas, veículos e passagens.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.foto import FotoRead
from app.schemas.passagem import PassagemVinculoRead
from app.schemas.pessoa import PessoaRead
from app.schemas.veiculo import VeiculoRead


class PassagemVinculoCreate(BaseModel):
    """Vinculação de passagem a pessoa durante criação de abordagem.

    Attributes:
        pessoa_id: ID da pessoa envolvida.
        passagem_id: ID da passagem/crime.
    """

    pessoa_id: int
    passagem_id: int


class AbordagemCreate(BaseModel):
    """Requisição de criação de abordagem.

    Payload único para registro rápido em campo (< 40 segundos).
    Permite vincular pessoas, veículos e passagens em uma única requisição.

    Attributes:
        data_hora: Data/hora da abordagem (timezone-aware).
        latitude: Latitude GPS (opcional).
        longitude: Longitude GPS (opcional).
        endereco_texto: Endereço em texto livre (auto-preenchido via geocoding reverso).
        observacao: Anotações do oficial.
        origem: Origem da criação ("online" ou "offline_sync").
        client_id: ID único do cliente (para deduplicação offline).
        pessoa_ids: IDs das pessoas abordadas.
        veiculo_ids: IDs dos veículos envolvidos.
        passagens: Vinculações de passagens a pessoas.
    """

    data_hora: datetime
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    endereco_texto: str | None = Field(None, max_length=500)
    observacao: str | None = None
    origem: str = Field("online", max_length=20)
    client_id: str | None = Field(None, max_length=100)
    pessoa_ids: list[int] = []
    veiculo_ids: list[int] = []
    passagens: list[PassagemVinculoCreate] = []


class AbordagemUpdate(BaseModel):
    """Requisição de atualização parcial de abordagem.

    Apenas campos de texto são editáveis pós-criação.

    Attributes:
        observacao: Anotações atualizadas.
        endereco_texto: Endereço em texto atualizado.
    """

    observacao: str | None = None
    endereco_texto: str | None = Field(None, max_length=500)


class AbordagemRead(BaseModel):
    """Dados públicos de uma abordagem (leitura).

    Attributes:
        id: Identificador único da abordagem.
        data_hora: Data/hora da abordagem.
        latitude: Latitude GPS.
        longitude: Longitude GPS.
        endereco_texto: Endereço em texto livre.
        observacao: Anotações do oficial.
        usuario_id: ID do oficial que realizou.
        guarnicao_id: ID da guarnição.
        origem: Origem ("online" ou "offline_sync").
        criado_em: Timestamp de criação.
        atualizado_em: Timestamp de última atualização.
    """

    id: int
    data_hora: datetime
    latitude: float | None = None
    longitude: float | None = None
    endereco_texto: str | None = None
    observacao: str | None = None
    usuario_id: int
    guarnicao_id: int
    origem: str
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class AbordagemDetail(AbordagemRead):
    """Dados detalhados de uma abordagem com todos os relacionamentos.

    Estende AbordagemRead com pessoas, veículos, fotos e passagens vinculadas.

    Attributes:
        pessoas: Lista de pessoas abordadas.
        veiculos: Lista de veículos envolvidos.
        fotos: Lista de fotos registradas.
        passagens: Lista de passagens vinculadas.
    """

    pessoas: list[PessoaRead] = []
    veiculos: list[VeiculoRead] = []
    fotos: list[FotoRead] = []
    passagens: list[PassagemVinculoRead] = []
