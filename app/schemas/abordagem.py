"""Schemas Pydantic para CRUD de Abordagem.

Define estruturas de requisição e resposta para criação, atualização,
leitura e busca de abordagens em campo, incluindo vinculação com
pessoas e veículos.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.foto import FotoRead
from app.schemas.ocorrencia import OcorrenciaRead
from app.schemas.veiculo import VeiculoRead


class AbordagemCreate(BaseModel):
    """Requisição de criação de abordagem.

    Payload único para registro rápido em campo (< 40 segundos).
    Permite vincular pessoas e veículos em uma única requisição.

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
        veiculo_por_pessoa: Mapeamento veiculo_id → pessoa_id (opcional).
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
    veiculo_por_pessoa: dict[int, int] = {}


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


class VeiculoAbordagemRead(VeiculoRead):
    """Veículo em uma abordagem com referência à pessoa associada.

    Estende VeiculoRead com o ID da pessoa que estava associada ao veículo
    na abordagem específica.

    Attributes:
        pessoa_id: ID da pessoa associada ao veículo nesta abordagem.
    """

    pessoa_id: int | None = None


class PessoaAbordagemRead(BaseModel):
    """Pessoa abordada com dados resumidos para exibição em card/detalhe.

    Versão compacta de PessoaRead usada nos cards de abordagem.
    Evita carregar todos os campos de Pessoa na listagem.

    Attributes:
        id: Identificador único da pessoa.
        nome: Nome completo.
        foto_principal_url: URL da foto de perfil (opcional).
        apelido: Apelido ou nome de rua (opcional).
    """

    id: int
    nome: str
    foto_principal_url: str | None = None
    apelido: str | None = None

    model_config = {"from_attributes": True}


class AbordagemDetail(AbordagemRead):
    """Dados detalhados de uma abordagem com todos os relacionamentos.

    Estende AbordagemRead com pessoas, veículos, fotos e ocorrências vinculadas.
    Usado para tela de detalhe e listagem de abordagens do usuário.

    Attributes:
        pessoas: Lista de pessoas abordadas (versão compacta).
        veiculos: Lista de veículos envolvidos com pessoa associada.
        fotos: Lista de fotos registradas (inclui mídias).
        ocorrencias: Lista de ocorrências (RAPs) vinculadas.
    """

    pessoas: list[PessoaAbordagemRead] = []
    veiculos: list[VeiculoAbordagemRead] = []
    fotos: list[FotoRead] = []
    ocorrencias: list[OcorrenciaRead] = []
