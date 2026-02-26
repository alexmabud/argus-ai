"""Testes unitários para o serviço de geração de embeddings.

Valida geração de embeddings individuais e em batch,
dimensões corretas e comportamento com cache.
"""

from unittest.mock import MagicMock, patch


class TestEmbeddingService:
    """Testes para EmbeddingService."""

    def test_gerar_embedding_retorna_lista(self):
        """Deve retornar lista de floats com 384 dimensões."""
        from app.services.embedding_service import EmbeddingService

        with patch.object(EmbeddingService, "__init__", lambda self: None):
            service = EmbeddingService()
            mock_model = MagicMock()
            mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
            service.model = mock_model
            service.redis_url = "redis://localhost:6379"
            service.cache_ttl = 3600

            result = service.gerar_embedding("texto teste")

            assert len(result) == 384
            assert all(isinstance(x, float) for x in result)
            mock_model.encode.assert_called_once_with("texto teste")

    def test_gerar_embeddings_batch(self):
        """Deve gerar embeddings para múltiplos textos em batch."""
        from app.services.embedding_service import EmbeddingService

        with patch.object(EmbeddingService, "__init__", lambda self: None):
            service = EmbeddingService()
            mock_model = MagicMock()
            mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 384, [0.2] * 384])
            service.model = mock_model
            service.redis_url = "redis://localhost:6379"
            service.cache_ttl = 3600

            textos = ["texto 1", "texto 2"]
            result = service.gerar_embeddings_batch(textos)

            assert len(result) == 2
            mock_model.encode.assert_called_once_with(textos)
