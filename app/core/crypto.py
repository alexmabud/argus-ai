"""Criptografia de dados sensíveis para conformidade LGPD.

Fornece funções para criptografia/descriptografia de campos sensíveis (CPF, etc)
usando Fernet (AES-256) e HMAC-SHA256 para buscas seguras sem descriptografar.
"""

import base64
import hashlib
import hmac
import logging

from cryptography.fernet import Fernet

from app.config import settings

_logger = logging.getLogger("argus")


def _validar_fernet_key(key: str) -> Fernet:
    """Valida e cria instância Fernet a partir da chave configurada.

    Verifica que a chave é base64 válida e tem exatamente 32 bytes
    (requisito Fernet). Falha com mensagem clara no startup em vez
    de falhar silenciosamente na primeira requisição.

    Args:
        key: Chave Fernet em formato base64 URL-safe.

    Returns:
        Instância Fernet validada.

    Raises:
        ValueError: Se a chave for inválida (formato ou tamanho).
    """
    try:
        decoded = base64.urlsafe_b64decode(key.encode())
    except Exception as exc:
        raise ValueError(
            "ENCRYPTION_KEY inválida: não é base64 URL-safe válido. "
            "Gere com: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        ) from exc

    if len(decoded) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY inválida: esperado 32 bytes, recebido {len(decoded)}. "
            "Gere com: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    fernet = Fernet(key.encode())
    _logger.info("Chave Fernet validada com sucesso")
    return fernet


_fernet = _validar_fernet_key(settings.ENCRYPTION_KEY)


def encrypt(value: str) -> str:
    """Criptografa um valor sensível usando Fernet (AES-256).

    Args:
        value: Valor em texto plano a criptografar (ex: CPF).

    Returns:
        String criptografada decodificada em base64.

    Raises:
        cryptography.fernet.InvalidToken: Se a chave for inválida.
    """

    return _fernet.encrypt(value.encode()).decode()


def decrypt(encrypted_value: str) -> str:
    """Descriptografa um valor previamente criptografado com Fernet.

    Args:
        encrypted_value: String criptografada em base64.

    Returns:
        Valor descriptografado em texto plano.

    Raises:
        cryptography.fernet.InvalidToken: Se o valor for inválido ou corrompido.
    """

    return _fernet.decrypt(encrypted_value.encode()).decode()


def hash_for_search(value: str) -> str:
    """Gera HMAC-SHA256 para busca exata sem descriptografar.

    Usa HMAC com SECRET_KEY como pepper para impedir ataques de rainbow
    table. O espaço de CPFs (~1 bilhão) é pequeno o suficiente para
    pré-computar SHA-256 puro em horas; HMAC torna isso inviável sem
    a chave secreta.

    Normaliza o valor removendo caracteres especiais (. e -) para permitir
    buscas de CPF independentemente do formato de entrada.

    Args:
        value: Valor a ser hasheado (ex: CPF com ou sem formatação).

    Returns:
        HMAC-SHA256 hexadecimal do valor normalizado.
    """
    normalized = value.strip().replace(".", "").replace("-", "")
    return hmac.new(settings.SECRET_KEY.encode(), normalized.encode(), hashlib.sha256).hexdigest()
