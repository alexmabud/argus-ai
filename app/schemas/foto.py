"""Schemas Pydantic para upload, leitura e busca de fotos.

Define estruturas de resposta para upload de fotos, listagem
de imagens associadas a pessoas e abordagens, busca por
similaridade facial e resultado de OCR de placas.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, field_validator

from app.services.storage_service import normalize_storage_url


class FotoTipo(StrEnum):
    """Tipos válidos de foto.

    Attributes:
        rosto: Foto de rosto para reconhecimento facial.
        corpo: Foto de corpo inteiro.
        placa: Foto de placa veicular.
        veiculo: Foto geral do veículo envolvido na abordagem.
        documento: Foto de documento.
    """

    rosto = "rosto"
    corpo = "corpo"
    placa = "placa"
    veiculo = "veiculo"
    documento = "documento"


class FotoRead(BaseModel):
    """Dados de leitura de uma foto.

    Attributes:
        id: Identificador único da foto.
        arquivo_url: URL da imagem no storage (R2/S3).
        tipo: Tipo de foto ("rosto", "corpo", "placa", etc).
        data_hora: Data/hora da captura.
        latitude: Latitude GPS da captura.
        longitude: Longitude GPS da captura.
        pessoa_id: ID da pessoa associada (null se só abordagem).
        abordagem_id: ID da abordagem associada (null se só pessoa).
        veiculo_id: ID do veículo associado (null se não for foto de veículo específico).
        face_processada: Flag se embedding facial foi extraído.
    """

    id: int
    arquivo_url: str
    tipo: str
    data_hora: datetime
    latitude: float | None = None
    longitude: float | None = None
    pessoa_id: int | None = None
    abordagem_id: int | None = None
    veiculo_id: int | None = None
    face_processada: bool

    _normalize_url = field_validator("arquivo_url", mode="before")(normalize_storage_url)

    model_config = {"from_attributes": True}


class FotoUploadResponse(BaseModel):
    """Resposta de upload de foto.

    Attributes:
        id: Identificador único da foto criada.
        arquivo_url: URL da imagem no storage.
        tipo: Tipo de foto.
    """

    id: int
    arquivo_url: str
    tipo: str

    _normalize_url = field_validator("arquivo_url", mode="before")(normalize_storage_url)


class BuscaRostoItem(BaseModel):
    """Item de resultado da busca por similaridade facial.

    Attributes:
        foto_id: ID da foto encontrada no banco.
        arquivo_url: URL da imagem no storage (R2/S3).
        pessoa_id: ID da pessoa associada à foto.
        similaridade: Grau de similaridade (0 a 1, cosseno).
        nome: Nome completo da pessoa (preenchido quando disponível).
        cpf_masked: CPF mascarado da pessoa (preenchido quando disponível).
        apelido: Apelido da pessoa (preenchido quando disponível).
        foto_principal_url: URL da foto de perfil da pessoa.
    """

    foto_id: int
    arquivo_url: str
    pessoa_id: int | None = None
    similaridade: float
    nome: str | None = None
    cpf_masked: str | None = None
    apelido: str | None = None
    foto_principal_url: str | None = None

    _normalize_urls = field_validator("arquivo_url", "foto_principal_url", mode="before")(
        normalize_storage_url
    )

    model_config = {"from_attributes": True}


class BuscaRostoResponse(BaseModel):
    """Resposta da busca por similaridade facial.

    Attributes:
        resultados: Lista de fotos similares ordenadas por similaridade.
        total: Quantidade de resultados retornados.
        disponivel: False quando InsightFace não está disponível no servidor.
    """

    resultados: list[BuscaRostoItem]
    total: int
    disponivel: bool = True


class OCRPlacaResponse(BaseModel):
    """Resposta da extração de placa via OCR.

    Attributes:
        placa: Placa detectada normalizada (ex: "ABC1D23") ou None.
        detectada: Flag indicando se uma placa foi encontrada.
    """

    placa: str | None = None
    detectada: bool
