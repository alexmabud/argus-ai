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

    def test_filename_longo_e_truncado(self):
        """Filenames muito longos devem ser truncados (~100 chars).

        Sem limite, atacante envia filename de 4KB que estoura S3 key ou
        Content-Disposition no download.
        """
        from app.api.v1.fotos import _sanitizar_filename

        result = _sanitizar_filename("a" * 500)
        assert len(result) <= 100

    def test_filename_unicode_rtl_removido(self):
        """Caracteres Unicode de controle (RTL override) sao removidos."""
        from app.api.v1.fotos import _sanitizar_filename

        result = _sanitizar_filename("teste‮evil.pdf")
        assert "‮" not in result
