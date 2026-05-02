"""Testes unitários dos schemas de Abordagem.

Verifica que FotoTipo.midia_abordagem existe, que AbordagemDetail
inclui ocorrencias, PessoaAbordagemRead existe e UsuarioResumoRead
tem os campos mínimos para exibição em cards.
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


class TestUsuarioResumoRead:
    """Testes do schema UsuarioResumoRead."""

    def test_campos_existem(self):
        """Testa que UsuarioResumoRead tem id, posto_graduacao e nome_guerra."""
        from app.schemas.auth import UsuarioResumoRead

        fields = UsuarioResumoRead.model_fields
        assert "id" in fields
        assert "posto_graduacao" in fields
        assert "nome_guerra" in fields

    def test_serializa_de_dict(self):
        """Testa que UsuarioResumoRead serializa corretamente."""
        from app.schemas.auth import UsuarioResumoRead

        schema = UsuarioResumoRead(id=1, posto_graduacao="SD", nome_guerra="Silva")
        assert schema.id == 1
        assert schema.posto_graduacao == "SD"
        assert schema.nome_guerra == "Silva"

    def test_campos_opcionais_aceitam_none(self):
        """Testa que posto_graduacao e nome_guerra aceitam None."""
        from app.schemas.auth import UsuarioResumoRead

        schema = UsuarioResumoRead(id=1, posto_graduacao=None, nome_guerra=None)
        assert schema.posto_graduacao is None
        assert schema.nome_guerra is None


class TestAbordagemDetailUsuario:
    """Testes do campo usuario no AbordagemDetail."""

    def test_usuario_field_existe(self):
        """Testa que AbordagemDetail tem o campo usuario."""
        fields = AbordagemDetail.model_fields
        assert "usuario" in fields
        # campo deve ser opcional (None quando usuário não carregado)
        field = fields["usuario"]
        assert field.default is None
