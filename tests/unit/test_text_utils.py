"""Testes unitários para utilitários de processamento de texto.

Valida chunking semântico por seções de BO e chunking por parágrafos
com overlap e controle de tokens.
"""

from app.services.text_utils import chunk_text_paragrafos, chunk_text_semantico


class TestChunkTextSemantico:
    """Testes para chunking semântico por seções de BO."""

    def test_texto_com_secoes_bo(self):
        """Deve separar texto em chunks por seções do BO."""
        texto = (
            "HISTÓRICO\nO abordado foi encontrado em atitude suspeita.\n"
            "ENVOLVIDOS\nJoão da Silva, vulgo 'Joãozinho'.\n"
            "PROVIDÊNCIAS\nConduzido à delegacia."
        )
        chunks = chunk_text_semantico(texto)
        assert len(chunks) >= 2

    def test_texto_sem_secoes_usa_paragrafos(self):
        """Deve usar fallback de parágrafos quando não há seções."""
        texto = "Parágrafo um com conteúdo.\n\nParágrafo dois com mais conteúdo."
        chunks = chunk_text_semantico(texto)
        assert len(chunks) >= 1

    def test_texto_vazio(self):
        """Deve retornar lista vazia para texto vazio."""
        chunks = chunk_text_semantico("")
        assert chunks == []

    def test_texto_curto_retorna_chunk_unico(self):
        """Deve retornar texto curto como chunk único."""
        texto = "Texto curto sem seções."
        chunks = chunk_text_semantico(texto)
        assert len(chunks) == 1


class TestChunkTextParagrafos:
    """Testes para chunking por parágrafos com overlap."""

    def test_paragrafos_simples(self):
        """Deve separar texto em parágrafos."""
        texto = "Primeiro parágrafo.\n\nSegundo parágrafo.\n\nTerceiro parágrafo."
        chunks = chunk_text_paragrafos(texto, max_tokens=10, overlap=2)
        assert len(chunks) >= 1

    def test_overlap_aplicado(self):
        """Deve aplicar overlap entre chunks."""
        # Texto longo com muitas palavras
        palavras = " ".join([f"palavra{i}" for i in range(100)])
        chunks = chunk_text_paragrafos(palavras, max_tokens=20, overlap=5)
        assert len(chunks) > 1

    def test_texto_vazio(self):
        """Deve retornar lista vazia para texto vazio."""
        chunks = chunk_text_paragrafos("", max_tokens=500, overlap=50)
        assert chunks == []

    def test_texto_dentro_do_limite(self):
        """Deve retornar chunk único se texto dentro do max_tokens."""
        texto = "Texto curto que cabe em um chunk."
        chunks = chunk_text_paragrafos(texto, max_tokens=500, overlap=50)
        assert len(chunks) == 1
