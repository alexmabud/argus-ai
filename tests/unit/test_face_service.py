"""Testes unitários para o serviço de reconhecimento facial.

Valida extração de embedding facial, comparação por similaridade
cosseno e tratamento de imagens sem rosto detectado.
"""

from unittest.mock import MagicMock, patch

import numpy as np


class TestFaceService:
    """Testes para FaceService."""

    def _make_service(self):
        """Cria instância de FaceService sem carregar modelo real."""
        from app.services.face_service import FaceService

        with patch.object(FaceService, "__init__", lambda self: None):
            service = FaceService()
            service.app = MagicMock()
            return service

    def test_extrair_embedding_com_rosto(self):
        """Deve retornar embedding de 512 dimensões quando rosto detectado."""
        service = self._make_service()
        mock_face = MagicMock()
        mock_face.det_score = 0.95
        mock_face.embedding = np.array([0.1] * 512)
        service.app.get.return_value = [mock_face]

        with patch("app.services.face_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            result = service.extrair_embedding(b"fake_image_bytes")

        assert result is not None
        assert len(result) == 512
        assert all(isinstance(x, float) for x in result)

    def test_extrair_embedding_sem_rosto(self):
        """Deve retornar None quando nenhum rosto é detectado."""
        service = self._make_service()
        service.app.get.return_value = []

        with patch("app.services.face_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            result = service.extrair_embedding(b"fake_image_bytes")

        assert result is None

    def test_extrair_embedding_seleciona_maior_score(self):
        """Deve selecionar rosto com maior det_score."""
        service = self._make_service()
        face_low = MagicMock()
        face_low.det_score = 0.5
        face_low.embedding = np.array([0.1] * 512)
        face_high = MagicMock()
        face_high.det_score = 0.99
        face_high.embedding = np.array([0.9] * 512)
        service.app.get.return_value = [face_low, face_high]

        with patch("app.services.face_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            result = service.extrair_embedding(b"fake_image_bytes")

        assert result is not None
        assert result[0] == float(np.float32(0.9))

    def test_comparar_identicos(self):
        """Similaridade cosseno de vetores idênticos deve ser ~1.0."""
        service = self._make_service()
        emb = [0.5] * 512

        score = service.comparar(emb, emb)

        assert abs(score - 1.0) < 1e-6

    def test_comparar_ortogonais(self):
        """Similaridade cosseno de vetores ortogonais deve ser ~0.0."""
        service = self._make_service()
        emb1 = [1.0] + [0.0] * 511
        emb2 = [0.0, 1.0] + [0.0] * 510

        score = service.comparar(emb1, emb2)

        assert abs(score) < 1e-6
