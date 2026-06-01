"""Testes dos schemas Pydantic de Pessoa para o campo nome_mae.

Valida que os schemas PessoaCreate e PessoaUpdate aceitam o novo campo
opcional nome_mae, respeitando o limite de 300 caracteres.
"""

from app.schemas.pessoa import PessoaCreate, PessoaUpdate


def test_pessoa_create_aceita_nome_mae():
    """PessoaCreate deve aceitar nome_mae (normalizado para maiúsculas)."""
    p = PessoaCreate(nome="Fulano", nome_mae="Maria")
    assert p.nome_mae == "MARIA"


def test_pessoa_create_nome_mae_opcional():
    """PessoaCreate deve permitir omitir nome_mae (default None)."""
    p = PessoaCreate(nome="Fulano")
    assert p.nome_mae is None


def test_pessoa_create_nome_mae_max_length():
    """PessoaCreate deve rejeitar nome_mae com mais de 300 caracteres."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PessoaCreate(nome="Fulano", nome_mae="x" * 301)


def test_pessoa_update_aceita_nome_mae():
    """PessoaUpdate deve aceitar nome_mae (normalizado para maiúsculas)."""
    p = PessoaUpdate(nome_mae="Nova Mae")
    assert p.nome_mae == "NOVA MAE"


# --- Padronização em MAIÚSCULAS -------------------------------------------


def test_pessoa_create_normaliza_nome_e_campos():
    """PessoaCreate normaliza nome, apelido, nome_mae e observações."""
    p = PessoaCreate(
        nome="joão silva",
        apelido="jão",
        nome_mae="maria silva",
        observacoes="usa boné azul",
    )
    assert p.nome == "JOÃO SILVA"
    assert p.apelido == "JÃO"
    assert p.nome_mae == "MARIA SILVA"
    assert p.observacoes == "USA BONÉ AZUL"


def test_pessoa_create_nao_afeta_cpf():
    """CPF não deve ser alterado pela normalização."""
    p = PessoaCreate(nome="joão", cpf="123.456.789-09")
    assert p.cpf == "123.456.789-09"


def test_pessoa_update_campos_opcionais_none():
    """PessoaUpdate normaliza o que vem e mantém None nos omitidos."""
    p = PessoaUpdate(nome="ana")
    assert p.nome == "ANA"
    assert p.apelido is None


def test_endereco_create_normaliza():
    """EnderecoCreate normaliza logradouro, bairro, cidade e UF."""
    from app.schemas.pessoa import EnderecoCreate

    e = EnderecoCreate(endereco="rua a, 10", bairro="centro", cidade="rio", estado="rj")
    assert e.endereco == "RUA A, 10"
    assert e.bairro == "CENTRO"
    assert e.cidade == "RIO"
    assert e.estado == "RJ"


# --- Task B4: foto_principal_thumb_url ------------------------------------


def _pessoa_read_data(**kwargs) -> dict:
    """Retorna dados mínimos válidos para PessoaRead."""
    from datetime import datetime

    base = {
        "id": 1,
        "nome": "Fulano",
        "criado_em": datetime(2026, 1, 1, 12, 0, 0),
        "atualizado_em": datetime(2026, 1, 1, 12, 0, 0),
    }
    base.update(kwargs)
    return base


def test_pessoa_read_expoe_foto_principal_thumb_url():
    """PessoaRead expõe foto_principal_thumb_url quando preenchido."""
    from app.schemas.pessoa import PessoaRead

    p = PessoaRead(
        **_pessoa_read_data(
            foto_principal_url="/storage/argus/perfil.jpg",
            foto_principal_thumb_url="/storage/argus/perfil_thumb.jpg",
        )
    )
    assert p.foto_principal_thumb_url == "/storage/argus/perfil_thumb.jpg"


def test_pessoa_read_foto_principal_thumb_url_default_none():
    """PessoaRead define foto_principal_thumb_url como None por padrão."""
    from app.schemas.pessoa import PessoaRead

    p = PessoaRead(**_pessoa_read_data())
    assert p.foto_principal_thumb_url is None


def test_pessoa_read_normaliza_foto_principal_thumb_url_absoluta():
    """PessoaRead normaliza URL absoluta legada do thumb para path relativo."""
    from app.config import settings
    from app.schemas.pessoa import PessoaRead

    p = PessoaRead(
        **_pessoa_read_data(
            foto_principal_thumb_url=(
                f"http://minio.local:9000/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"
            ),
        )
    )
    assert p.foto_principal_thumb_url == f"/storage/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"


def test_vinculo_read_expoe_foto_principal_thumb_url():
    """VinculoRead expõe e normaliza foto_principal_thumb_url."""
    from datetime import datetime

    from app.config import settings
    from app.schemas.pessoa import VinculoRead

    v = VinculoRead(
        pessoa_id=1,
        nome="Fulano",
        frequencia=3,
        ultima_vez=datetime(2026, 1, 1, 12, 0, 0),
        foto_principal_url="/storage/argus/perfil.jpg",
        foto_principal_thumb_url=(
            f"http://minio.local:9000/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"
        ),
    )
    assert v.foto_principal_thumb_url == f"/storage/{settings.S3_BUCKET}/fotos/perfil_thumb.jpg"
