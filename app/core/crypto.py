"""Criptografia de dados sensíveis para conformidade LGPD.

Fornece funções para criptografia/descriptografia de campos sensíveis (CPF, etc)
usando Fernet (AES-256) e hashing SHA-256 para buscas seguras sem descriptografar.
"""

import hashlib

from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


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
    """Gera hash SHA-256 para busca exata sem descriptografar.

    Normaliza o valor removendo caracteres especiais (. e -) para permitir
    buscas de CPF independentemente do formato de entrada, mantendo segurança
    pois não requer descriptografia para comparação.

    Args:
        value: Valor a ser hasheado (ex: CPF com ou sem formatação).

    Returns:
        Hash SHA-256 hexadecimal do valor normalizado.
    """

    normalized = value.strip().replace(".", "").replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
