"""Testes do filtro de redacao de PII/secrets em logs.

Garante que mensagens de log nao vazem JWT, CPF, senhas ou Authorization
headers — vetor de vazamento LGPD via Loki/Telegram/agregadores.
"""

import logging

from app.core.logging_config import RedactFilter


def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="argus", level=logging.INFO, pathname="", lineno=0,
        msg=msg, args=(), exc_info=None,
    )


def test_redact_jwt_bearer_authorization():
    """JWT em Authorization header deve ser substituido por marcador."""
    f = RedactFilter()
    rec = _make_record("Authorization: Bearer eyJabc.def.ghi")
    f.filter(rec)
    assert "eyJabc" not in rec.getMessage()
    assert "REDACTED" in rec.getMessage()


def test_redact_cpf_formatado():
    """CPF no formato XXX.XXX.XXX-XX deve ter o miolo mascarado."""
    f = RedactFilter()
    rec = _make_record("User CPF 123.456.789-01 found")
    f.filter(rec)
    assert "456.789" not in rec.getMessage()


def test_redact_senha_em_json():
    """Campo `senha` em JSON deve ser substituido."""
    f = RedactFilter()
    rec = _make_record('{"matricula": "abc", "senha": "minhasenha123"}')
    f.filter(rec)
    assert "minhasenha123" not in rec.getMessage()


def test_redact_password_em_json():
    """Campo `password` em JSON tambem deve ser substituido."""
    f = RedactFilter()
    rec = _make_record('{"user": "x", "password": "p4ssw0rd!"}')
    f.filter(rec)
    assert "p4ssw0rd!" not in rec.getMessage()


def test_redact_jwt_solto_no_corpo():
    """JWT solto (sem header Authorization) deve ser detectado."""
    f = RedactFilter()
    rec = _make_record("Token recebido: eyJhbGciOiJIUzI1NiJ9.payload.signature")
    f.filter(rec)
    assert "eyJhbGciOiJIUzI1NiJ9" not in rec.getMessage()


def test_redact_preserva_mensagem_sem_segredos():
    """Mensagens sem PII/secrets nao devem ser alteradas."""
    f = RedactFilter()
    rec = _make_record("Abordagem criada com sucesso")
    f.filter(rec)
    assert rec.getMessage() == "Abordagem criada com sucesso"
