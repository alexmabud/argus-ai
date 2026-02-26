"""Schemas Pydantic para CRUD de Ocorrência (boletim de ocorrência).

Define estruturas de requisição e resposta para upload de PDF,
leitura e busca semântica de ocorrências policiais.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OcorrenciaCreate(BaseModel):
    """Requisição de criação de ocorrência.

    O arquivo PDF é enviado via multipart/form-data no router,
    não neste schema.

    Attributes:
        numero_ocorrencia: Número único do BO (ex: "2024.0001234-5").
        abordagem_id: ID da abordagem associada.
    """

    numero_ocorrencia: str = Field(..., min_length=1, max_length=50)
    abordagem_id: int


class OcorrenciaRead(BaseModel):
    """Dados de leitura de uma ocorrência.

    Attributes:
        id: Identificador único.
        numero_ocorrencia: Número do BO.
        abordagem_id: ID da abordagem associada.
        arquivo_pdf_url: URL do PDF em S3/R2.
        processada: Se o PDF já foi extraído e embedado.
        usuario_id: ID do usuário que cadastrou.
        guarnicao_id: ID da guarnição.
        criado_em: Timestamp de criação.
        atualizado_em: Timestamp de última atualização.
    """

    id: int
    numero_ocorrencia: str
    abordagem_id: int
    arquivo_pdf_url: str
    processada: bool
    usuario_id: int
    guarnicao_id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class OcorrenciaDetail(OcorrenciaRead):
    """Dados detalhados de ocorrência com texto extraído.

    Estende OcorrenciaRead com o texto extraído do PDF e score
    de similaridade (quando retornado de busca semântica).

    Attributes:
        texto_extraido: Texto completo extraído do PDF via PyMuPDF.
        similaridade: Score de similaridade cosseno (0-1) quando
            retornado de busca semântica. None para leitura direta.
    """

    texto_extraido: str | None = None
    similaridade: float | None = None
