"""Testes unitários dos schemas de Foto."""

from app.schemas.foto import BuscaRostoItem


def _base_data(**kwargs) -> dict:
    """Retorna dados mínimos válidos para BuscaRostoItem."""
    return {
        "foto_id": 1,
        "arquivo_url": "https://r2.example.com/foto.jpg",
        "similaridade": 0.95,
        **kwargs,
    }


def test_busca_rosto_item_campos_obrigatorios():
    """BuscaRostoItem funciona com apenas campos obrigatórios."""
    item = BuscaRostoItem(**_base_data())
    assert item.foto_id == 1
    assert item.arquivo_url == "https://r2.example.com/foto.jpg"
    assert item.similaridade == 0.95
    assert item.pessoa_id is None
    assert item.nome is None
    assert item.cpf_masked is None
    assert item.apelido is None
    assert item.foto_principal_url is None


def test_busca_rosto_item_campos_opcionais():
    """BuscaRostoItem aceita e armazena campos opcionais."""
    item = BuscaRostoItem(
        **_base_data(
            pessoa_id=42,
            nome="João da Silva",
            cpf_masked="123.456.789-**",
            apelido="Joãozinho",
            foto_principal_url="https://r2.example.com/perfil.jpg",
        )
    )
    assert item.foto_id == 1
    assert item.arquivo_url == "https://r2.example.com/foto.jpg"
    assert item.pessoa_id == 42
    assert item.similaridade == 0.95
    assert item.nome == "João da Silva"
    assert item.cpf_masked == "123.456.789-**"
    assert item.apelido == "Joãozinho"
    assert item.foto_principal_url == "https://r2.example.com/perfil.jpg"


def test_busca_rosto_item_from_attributes():
    """BuscaRostoItem suporta criação a partir de atributos (ORM)."""

    # Simula um objeto ORM com atributos
    class MockFoto:
        foto_id = 1
        arquivo_url = "https://r2.example.com/foto.jpg"
        pessoa_id = 42
        similaridade = 0.87
        nome = "Maria Santos"
        cpf_masked = "987.654.321-**"
        apelido = "Mari"
        foto_principal_url = "https://r2.example.com/maria.jpg"

    item = BuscaRostoItem.model_validate(MockFoto())
    assert item.foto_id == 1
    assert item.pessoa_id == 42
    assert item.nome == "Maria Santos"
    assert item.cpf_masked == "987.654.321-**"


def test_busca_rosto_item_campos_opcionais_parciais():
    """BuscaRostoItem funciona com apenas alguns campos opcionais preenchidos."""
    item = BuscaRostoItem(**_base_data(pessoa_id=10, nome="Pedro"))
    assert item.pessoa_id == 10
    assert item.nome == "Pedro"
    assert item.cpf_masked is None
    assert item.apelido is None
    assert item.foto_principal_url is None
