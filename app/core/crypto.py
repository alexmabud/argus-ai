import hashlib

from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    """Criptografa valor sensível (CPF, etc)."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(encrypted_value: str) -> str:
    """Descriptografa valor."""
    return _fernet.decrypt(encrypted_value.encode()).decode()


def hash_for_search(value: str) -> str:
    """Gera hash SHA-256 para busca exata sem descriptografar."""
    normalized = value.strip().replace(".", "").replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
