"""Schemas Pydantic para CRUD de Pessoa e Endereço.

Define estruturas de requisição e resposta para criação, atualização,
leitura e busca de pessoas e seus endereços associados.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class PessoaCreate(BaseModel):
    """Requisição de criação de pessoa.

    Attributes:
        nome: Nome completo da pessoa (2 a 300 caracteres).
        cpf: CPF em texto plano (será criptografado no serviço). Opcional.
        data_nascimento: Data de nascimento (opcional).
        apelido: Apelido ou "nome de rua" (opcional, até 100 caracteres).
        observacoes: Anotações sobre a pessoa (opcional).
    """

    nome: str = Field(..., min_length=2, max_length=300)
    cpf: str | None = Field(None, max_length=14)
    data_nascimento: date | None = None
    apelido: str | None = Field(None, max_length=100)
    observacoes: str | None = None


class PessoaUpdate(BaseModel):
    """Requisição de atualização parcial de pessoa.

    Todos os campos são opcionais. Apenas os campos enviados serão atualizados.

    Attributes:
        nome: Nome completo atualizado.
        cpf: CPF em texto plano (será re-criptografado). Opcional.
        data_nascimento: Data de nascimento atualizada.
        apelido: Apelido atualizado.
        observacoes: Anotações atualizadas.
    """

    nome: str | None = Field(None, min_length=2, max_length=300)
    cpf: str | None = Field(None, max_length=14)
    data_nascimento: date | None = None
    apelido: str | None = Field(None, max_length=100)
    observacoes: str | None = None


class PessoaRead(BaseModel):
    """Dados públicos de uma pessoa (leitura).

    CPF nunca é retornado em texto plano. Apenas os últimos 2 dígitos
    são exibidos no campo cpf_masked para conformidade LGPD.

    Attributes:
        id: Identificador único da pessoa.
        nome: Nome completo.
        cpf_masked: CPF mascarado (ex: "***.***.***-34"). Null se sem CPF.
        data_nascimento: Data de nascimento.
        apelido: Apelido ou "nome de rua".
        foto_principal_url: URL da foto de perfil (R2/S3).
        observacoes: Anotações sobre a pessoa.
        guarnicao_id: ID da guarnição.
        criado_em: Timestamp de criação.
        atualizado_em: Timestamp de última atualização.
    """

    id: int
    nome: str
    cpf_masked: str | None = None
    data_nascimento: date | None = None
    apelido: str | None = None
    foto_principal_url: str | None = None
    observacoes: str | None = None
    guarnicao_id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class EnderecoCreate(BaseModel):
    """Requisição de criação de endereço para pessoa.

    Attributes:
        endereco: Endereço em texto livre (até 500 caracteres).
        latitude: Latitude GPS (opcional, para PostGIS).
        longitude: Longitude GPS (opcional, para PostGIS).
        data_inicio: Data de início da associação com endereço.
        data_fim: Data de fim da associação com endereço.
    """

    endereco: str = Field(..., min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    data_inicio: date | None = None
    data_fim: date | None = None


class EnderecoRead(BaseModel):
    """Dados de leitura de um endereço de pessoa.

    Attributes:
        id: Identificador único do endereço.
        endereco: Endereço em texto livre.
        data_inicio: Data de início da associação.
        data_fim: Data de fim da associação.
        criado_em: Timestamp de criação.
    """

    id: int
    endereco: str
    data_inicio: date | None = None
    data_fim: date | None = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class PessoaDetail(PessoaRead):
    """Dados detalhados de uma pessoa com relacionamentos.

    Estende PessoaRead com endereços, contagem de abordagens e
    vínculos com outras pessoas.

    Attributes:
        enderecos: Lista de endereços conhecidos.
        abordagens_count: Número total de abordagens.
        relacionamentos: Lista simplificada de vínculos (pessoa, frequência).
    """

    enderecos: list[EnderecoRead] = []
    abordagens_count: int = 0
    relacionamentos: list[VinculoRead] = []


class VinculoRead(BaseModel):
    """Vínculo simplificado entre pessoas para exibição em detail.

    Attributes:
        pessoa_id: ID da pessoa vinculada.
        nome: Nome da pessoa vinculada.
        frequencia: Número de vezes abordadas juntas.
        ultima_vez: Timestamp da última abordagem conjunta.
    """

    pessoa_id: int
    nome: str
    frequencia: int
    ultima_vez: datetime
