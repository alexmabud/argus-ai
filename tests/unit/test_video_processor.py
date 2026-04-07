"""Testes unitários para processamento de vídeo."""

import pytest


class TestDetectarVideo:
    """Testes para detecção de MIME types de vídeo."""

    def test_mp4_e_video(self):
        """video/mp4 deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("video/mp4") is True

    def test_quicktime_e_video(self):
        """video/quicktime deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("video/quicktime") is True

    def test_webm_e_video(self):
        """video/webm deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("video/webm") is True

    def test_avi_e_video(self):
        """video/x-msvideo deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("video/x-msvideo") is True

    def test_imagem_nao_e_video(self):
        """image/jpeg não deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("image/jpeg") is False

    def test_pdf_nao_e_video(self):
        """application/pdf não deve ser reconhecido como vídeo."""
        from app.tasks.video_processor import _e_video

        assert _e_video("application/pdf") is False


class TestComprimir:
    """Testes para compressão de vídeo via ffmpeg."""

    @pytest.mark.asyncio
    async def test_comprimir_retorna_bytes(self, tmp_path):
        """_comprimir_video_sincrono deve retornar bytes válidos."""
        import subprocess

        # Criar vídeo de teste válido com ffmpeg
        video_path = tmp_path / "test.mp4"
        result = subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x240:d=2",
                "-c:v",
                "libx264",
                "-t",
                "2",
                str(video_path),
                "-y",
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            pytest.skip("ffmpeg não disponível no ambiente de teste")

        video_bytes = video_path.read_bytes()
        from app.tasks.video_processor import _comprimir_video_sincrono

        compressed = _comprimir_video_sincrono(video_bytes)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

    def test_comprimir_falha_se_ffmpeg_erro(self, tmp_path):
        """_comprimir_video_sincrono deve levantar RuntimeError se ffmpeg falhar."""
        from unittest.mock import MagicMock, patch

        from app.tasks.video_processor import _comprimir_video_sincrono

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"erro simulado do ffmpeg"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="ffmpeg falhou"):
                _comprimir_video_sincrono(b"fake video bytes")

    def test_comprimir_falha_se_saida_vazia(self, tmp_path):
        """_comprimir_video_sincrono deve levantar RuntimeError se ffmpeg produzir arquivo vazio.

        O arquivo de saída é criado vazio pelo side_effect para que saida.read_bytes()
        retorne b"" e acione a guarda RuntimeError("ffmpeg produziu arquivo vazio").
        Se o arquivo não existisse, seria levantado FileNotFoundError em vez disso.
        """
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from app.tasks.video_processor import _comprimir_video_sincrono

        mock_result = MagicMock()
        mock_result.returncode = 0

        def fake_run(cmd, **kwargs):
            # Localiza o argumento de saída no comando ffmpeg (último elemento)
            # e cria o arquivo vazio para simular saída vazia do ffmpeg
            output_path = Path(cmd[-1])
            output_path.write_bytes(b"")
            return mock_result

        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="arquivo vazio"):
                _comprimir_video_sincrono(b"fake video bytes")
