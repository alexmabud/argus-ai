"""Schemas Pydantic para upload, leitura e busca de fotos.

Define estruturas de resposta para upload de fotos, listagem
de imagens associadas a pessoas e abordagens, busca por
similaridade facial e resultado de OCR de placas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
    face_processada: bool

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


class BuscaRostoItem(BaseModel):
    """Item de resultado da busca por similaridade facial.

    Attributes:
        foto_id: ID da foto encontrada no banco.
        arquivo_url: URL da imagem no storage (R2/S3).
        pessoa_id: ID da pessoa associada à foto.
        similaridade: Grau de similaridade (0 a 1, cosseno).
    """

    foto_id: int
    arquivo_url: str
    pessoa_id: int | None = None
    similaridade: float

    model_config = {"from_attributes": True}


class BuscaRostoResponse(BaseModel):
    """Resposta da busca por similaridade facial.

    Attributes:
        resultados: Lista de fotos similares ordenadas por similaridade.
        total: Quantidade de resultados retornados.
    """

    resultados: list[BuscaRostoItem]
    total: int


class OCRPlacaResponse(BaseModel):
    """Resposta da extração de placa via OCR.

    Attributes:
        placa: Placa detectada normalizada (ex: "ABC1D23") ou None.
        detectada: Flag indicando se uma placa foi encontrada.
    """

    placa: str | None = None
    detectada: bool
