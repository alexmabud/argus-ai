"""Testes para o router de fotos — enfileiramento de compressão."""


class TestUploadMidiaEnfileira:
    """Verifica que upload de vídeo enfileira compressão."""

    def test_e_video_mp4(self):
        """_e_video deve retornar True para video/mp4."""
        from app.tasks.video_processor import _e_video

        assert _e_video("video/mp4") is True

    def test_e_video_imagem_false(self):
        """_e_video deve retornar False para image/jpeg."""
        from app.tasks.video_processor import _e_video

        assert _e_video("image/jpeg") is False
