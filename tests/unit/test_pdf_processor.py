"""Testes unitários para processamento de PDF.

Valida extração de texto e parsing de URL S3 para chave.
"""

import pytest

from app.tasks.pdf_processor import extrair_texto_pdf
from app.utils.s3 import extrair_key_da_url


class TestExtrairKeyDaUrl:
    """Testes para extração de chave S3 a partir de URL."""

    def test_url_com_bucket_e_key(self):
        """Deve extrair chave removendo endpoint e bucket."""
        url = "https://r2.example.com/argus/pdfs/abc123_doc.pdf"
        key = extrair_key_da_url(url)
        assert key == "pdfs/abc123_doc.pdf"

    def test_url_com_path_simples(self):
        """Deve funcionar com URLs de path simples."""
        url = "https://r2.example.com/bucket/file.pdf"
        key = extrair_key_da_url(url)
        assert key == "file.pdf"

    def test_url_producao_com_prefixo_proxy(self, monkeypatch):
        """Deve extrair chave corretamente quando S3_PUBLIC_URL tem prefixo de proxy reverso.

        Reproduz o bug de produção onde S3_PUBLIC_URL=https://dominio.com/storage
        faz o path ter um segmento extra (/storage) que o split antigo ignorava,
        retornando '{bucket}/{key}' em vez de apenas '{key}'.
        """
        from app.config import settings

        monkeypatch.setattr(settings, "S3_PUBLIC_URL", "https://arguseye.duckdns.org/storage")
        monkeypatch.setattr(settings, "S3_BUCKET", "argus")

        url = "https://arguseye.duckdns.org/storage/argus/pdfs/abc123_doc.pdf"
        key = extrair_key_da_url(url)
        assert key == "pdfs/abc123_doc.pdf"


class TestExtrairTextoPdf:
    """Testes para extração de texto de PDF via PyMuPDF."""

    def test_pdf_bytes_invalido(self):
        """Deve levantar exceção para bytes não-PDF."""
        with pytest.raises(Exception):
            extrair_texto_pdf(b"nao sou um pdf")

    def test_extrai_texto_de_pdf_simples(self):
        """Caminho feliz: extrai o texto de um PDF de uma página."""
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Boletim de Ocorrencia teste")
        pdf_bytes = doc.tobytes()
        doc.close()

        texto = extrair_texto_pdf(pdf_bytes)
        assert "Boletim de Ocorrencia teste" in texto

    def test_respeita_teto_de_paginas(self, monkeypatch):
        """PDF acima do teto de páginas processa só as primeiras N (achado #17/2026-07-13)."""
        import fitz

        from app.tasks import pdf_processor

        monkeypatch.setattr(pdf_processor, "MAX_PDF_PAGES", 3)

        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"pagina-{i}")
        pdf_bytes = doc.tobytes()
        doc.close()

        texto = pdf_processor.extrair_texto_pdf(pdf_bytes)
        assert "pagina-0" in texto
        assert "pagina-2" in texto
        assert "pagina-3" not in texto
        assert "pagina-4" not in texto
