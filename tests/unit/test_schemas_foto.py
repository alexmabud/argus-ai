"""Testes unitários dos schemas de Foto."""

from datetime import datetime

from app.schemas.foto import BuscaRostoItem, FotoRead, FotoUploadResponse


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


# --- Task B4: thumbnail_url / foto_principal_thumb_url ---------------------


def _foto_read_data(**kwargs) -> dict:
    """Retorna dados mínimos válidos para FotoRead."""
    base = {
        "id": 1,
        "arquivo_url": "/storage/argus/foto.jpg",
        "tipo": "rosto",
        "data_hora": datetime(2026, 1, 1, 12, 0, 0),
        "face_processada": False,
    }
    base.update(kwargs)
    return base


def test_foto_read_serializa_thumbnail_url():
    """FotoRead expõe thumbnail_url quando o campo é fornecido."""
    foto = FotoRead(**_foto_read_data(thumbnail_url="/storage/argus/foto_thumb.jpg"))
    assert foto.thumbnail_url == "/storage/argus/foto_thumb.jpg"


def test_foto_read_aceita_thumbnail_url_none():
    """FotoRead aceita thumbnail_url=None (default)."""
    foto = FotoRead(**_foto_read_data())
    assert foto.thumbnail_url is None


def test_foto_read_normaliza_thumbnail_url_absoluta_legada():
    """FotoRead converte URL absoluta legada de thumbnail para path relativo."""
    from app.config import settings

    foto = FotoRead(
        **_foto_read_data(
            thumbnail_url=f"http://minio.local:9000/{settings.S3_BUCKET}/fotos/abc_thumb.jpg"
        )
    )
    assert foto.thumbnail_url == f"/storage/{settings.S3_BUCKET}/fotos/abc_thumb.jpg"


def test_foto_upload_response_expoe_thumbnail_url():
    """FotoUploadResponse expõe thumbnail_url quando preenchido."""
    resp = FotoUploadResponse(
        id=10,
        arquivo_url="/storage/argus/foto.jpg",
        thumbnail_url="/storage/argus/foto_thumb.jpg",
        tipo="rosto",
    )
    assert resp.thumbnail_url == "/storage/argus/foto_thumb.jpg"


def test_foto_upload_response_thumbnail_url_default_none():
    """FotoUploadResponse aceita omitir thumbnail_url (default None)."""
    resp = FotoUploadResponse(
        id=10,
        arquivo_url="/storage/argus/foto.jpg",
        tipo="rosto",
    )
    assert resp.thumbnail_url is None


def test_busca_rosto_item_expoe_thumbnail_urls():
    """BuscaRostoItem expõe thumbnail_url e foto_principal_thumb_url."""
    item = BuscaRostoItem(
        **_base_data(
            thumbnail_url="https://r2.example.com/foto_thumb.jpg",
            pessoa_id=7,
            foto_principal_url="https://r2.example.com/perfil.jpg",
            foto_principal_thumb_url="https://r2.example.com/perfil_thumb.jpg",
        )
    )
    assert item.thumbnail_url == "https://r2.example.com/foto_thumb.jpg"
    assert item.foto_principal_thumb_url == "https://r2.example.com/perfil_thumb.jpg"


def test_busca_rosto_item_thumb_urls_default_none():
    """BuscaRostoItem mantém os novos campos como None por padrão."""
    item = BuscaRostoItem(**_base_data())
    assert item.thumbnail_url is None
    assert item.foto_principal_thumb_url is None


def test_busca_rosto_item_normaliza_thumb_urls_absolutas():
    """BuscaRostoItem normaliza URLs absolutas legadas dos campos thumb."""
    from app.config import settings

    item = BuscaRostoItem(
        **_base_data(
            thumbnail_url=f"http://minio.local:9000/{settings.S3_BUCKET}/fotos/a_thumb.jpg",
            foto_principal_thumb_url=(
                f"http://minio.local:9000/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"
            ),
        )
    )
    assert item.thumbnail_url == f"/storage/{settings.S3_BUCKET}/fotos/a_thumb.jpg"
    assert item.foto_principal_thumb_url == f"/storage/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"
