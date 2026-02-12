"""Schemas Pydantic para upload e leitura de fotos.

Define estruturas de resposta para upload de fotos e listagem
de imagens associadas a pessoas e abordagens.
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
