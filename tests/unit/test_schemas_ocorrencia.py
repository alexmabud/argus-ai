"""Testes unitários dos schemas de Ocorrência."""

from datetime import datetime

from app.schemas.ocorrencia import OcorrenciaRead


def _base_data(**kwargs) -> dict:
    """Retorna dados mínimos válidos para OcorrenciaRead."""
    return {
        "id": 1,
        "numero_ocorrencia": "RAP 2026/000001",
        "abordagem_id": None,
        "arquivo_pdf_url": "https://r2.example.com/test.pdf",
        "processada": False,
        "usuario_id": 1,
        "guarnicao_id": 1,
        "criado_em": datetime(2026, 1, 1),
        "atualizado_em": datetime(2026, 1, 1),
        **kwargs,
    }


def test_parse_nomes_none():
    """None vira lista vazia."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=None))
    assert oc.nomes_envolvidos == []


def test_parse_nomes_vazio():
    """String vazia vira lista vazia."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=""))
    assert oc.nomes_envolvidos == []


def test_parse_nomes_um():
    """String com um nome vira lista de um elemento."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos="João da Silva"))
    assert oc.nomes_envolvidos == ["João da Silva"]


def test_parse_nomes_multiplos():
    """String pipe-separated vira lista de nomes."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos="João da Silva|Maria Souza|Pedro Lima"))
    assert oc.nomes_envolvidos == ["João da Silva", "Maria Souza", "Pedro Lima"]


def test_parse_nomes_espacos_extras():
    """Espaços ao redor do pipe são removidos."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos=" João  | Maria "))
    assert oc.nomes_envolvidos == ["João", "Maria"]


def test_parse_nomes_pipes_duplos():
    """Pipes duplos (segmentos vazios) são ignorados."""
    oc = OcorrenciaRead(**_base_data(nomes_envolvidos="João||Maria"))
    assert oc.nomes_envolvidos == ["João", "Maria"]
