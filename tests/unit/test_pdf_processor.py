"""Testes unitários para processamento de PDF.

Valida extração de texto e parsing de URL S3 para chave.
"""

import pytest

from app.tasks.pdf_processor import _extrair_key_da_url, extrair_texto_pdf


class TestExtrairKeyDaUrl:
    """Testes para extração de chave S3 a partir de URL."""

    def test_url_com_bucket_e_key(self):
        """Deve extrair chave removendo endpoint e bucket."""
        url = "https://r2.example.com/argus/pdfs/abc123_doc.pdf"
        key = _extrair_key_da_url(url)
        assert key == "pdfs/abc123_doc.pdf"

    def test_url_com_path_simples(self):
        """Deve funcionar com URLs de path simples."""
        url = "https://r2.example.com/bucket/file.pdf"
        key = _extrair_key_da_url(url)
        assert key == "file.pdf"


class TestExtrairTextoPdf:
    """Testes para extração de texto de PDF via PyMuPDF."""

    def test_pdf_bytes_invalido(self):
        """Deve levantar exceção para bytes não-PDF."""
        with pytest.raises(Exception):
            extrair_texto_pdf(b"nao sou um pdf")
