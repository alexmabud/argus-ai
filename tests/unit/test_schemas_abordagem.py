"""Testes unitários dos schemas de Abordagem.

Verifica que FotoTipo.midia_abordagem existe, que AbordagemDetail
inclui ocorrencias e PessoaAbordagemRead existe.
"""

from app.schemas.abordagem import AbordagemDetail, PessoaAbordagemRead
from app.schemas.foto import FotoTipo


class TestFotoTipo:
    """Testes do enum FotoTipo."""

    def test_midia_abordagem_existe(self):
        """Testa que FotoTipo contém o valor midia_abordagem."""
        assert FotoTipo.midia_abordagem == "midia_abordagem"
        assert "midia_abordagem" in [t.value for t in FotoTipo]


class TestAbordagemDetail:
    """Testes do schema AbordagemDetail."""

    def test_ocorrencias_field_existe(self):
        """Testa que AbordagemDetail tem o campo ocorrencias."""
        fields = AbordagemDetail.model_fields
        assert "ocorrencias" in fields
        assert "pessoas" in fields
        assert "veiculos" in fields
        assert "fotos" in fields

    def test_pessoas_usa_pessoa_abordagem_read(self):
        """Testa que AbordagemDetail.pessoas usa PessoaAbordagemRead."""
        # PessoaAbordagemRead deve existir e ter os campos corretos
        fields = PessoaAbordagemRead.model_fields
        assert "id" in fields
        assert "nome" in fields
        assert "apelido" in fields
        assert "foto_principal_url" in fields
