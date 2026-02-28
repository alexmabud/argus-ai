"""Serviço de reconhecimento facial via InsightFace.

Carrega modelo buffalo_l para detecção e embedding facial (512 dimensões).
Usado para busca por similaridade facial via pgvector e identificação
de pessoas em abordagens.
"""

import io
import logging

import numpy as np
from PIL import Image

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None

logger = logging.getLogger("argus")


class FaceService:
    """Serviço de embedding e comparação facial via InsightFace.

    Carrega modelo buffalo_l (detector + reconhecimento) em memória
    e gera embeddings faciais de 512 dimensões para busca por
    similaridade via pgvector.

    Attributes:
        app: Instância FaceAnalysis com modelo buffalo_l carregado.
    """

    def __init__(self):
        """Inicializa serviço carregando modelo InsightFace.

        Carrega modelo buffalo_l com ONNX Runtime (CPU).
        O modelo fica em memória durante todo o ciclo de vida da aplicação.
        """
        if FaceAnalysis is None:
            raise ImportError("InsightFace não instalado")

        logger.info("Carregando modelo InsightFace (buffalo_l)...")
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("Modelo InsightFace carregado com sucesso")

    def extrair_embedding(self, image_bytes: bytes) -> list[float] | None:
        """Extrai embedding facial de uma imagem.

        Detecta rostos na imagem e retorna o embedding de 512 dimensões
        do rosto com maior score de detecção. Retorna None se nenhum
        rosto for detectado.

        Args:
            image_bytes: Conteúdo da imagem em bytes (JPEG, PNG, etc).

        Returns:
            Lista de 512 floats representando o embedding facial,
            ou None se nenhum rosto foi detectado.
        """
        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        faces = self.app.get(img)

        if not faces:
            return None

        # Selecionar rosto com maior confiança de detecção
        face = max(faces, key=lambda f: f.det_score)
        return face.embedding.tolist()

    def comparar(self, emb1: list[float], emb2: list[float]) -> float:
        """Calcula similaridade cosseno entre dois embeddings faciais.

        Args:
            emb1: Embedding facial 512-dimensional.
            emb2: Embedding facial 512-dimensional.

        Returns:
            Score de similaridade entre 0.0 e 1.0.
        """
        a, b = np.array(emb1), np.array(emb2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
