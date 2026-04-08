"""Testes para o endpoint de download de mídia."""


class TestSanitizarFilename:
    """Testa sanitização de nomes de arquivo para Content-Disposition."""

    def test_filename_simples(self):
        """Filename simples não deve ser alterado."""
        from app.api.v1.fotos import _sanitizar_filename

        assert _sanitizar_filename("video.mp4") == "video.mp4"

    def test_filename_com_path_traversal(self):
        """Path traversal deve ser removido."""
        from app.api.v1.fotos import _sanitizar_filename

        result = _sanitizar_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_filename_vazio_retorna_default(self):
        """Filename vazio deve retornar 'midia'."""
        from app.api.v1.fotos import _sanitizar_filename

        assert _sanitizar_filename("") == "midia"

    def test_filename_com_espacos(self):
        """Espaços no filename devem ser substituídos por underscore."""
        from app.api.v1.fotos import _sanitizar_filename

        result = _sanitizar_filename("meu video da abordagem.mp4")
        assert " " not in result
