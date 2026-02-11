"""Utilitários de segurança para hashing de senhas e geração de tokens JWT.

Fornece funções para hashing de senhas com bcrypt, verificação de credenciais
e criação/validação de tokens JWT para fluxos de autenticação e autorização.
"""

from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Faz hash de uma senha usando bcrypt.

    Args:
        senha: Senha em texto plano a ser hasheada.

    Returns:
        String de hash bcrypt adequada para armazenamento em banco de dados.
    """

    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    """Verifica uma senha em texto plano contra um hash bcrypt.

    Args:
        senha: Senha em texto plano a verificar.
        hash: Hash bcrypt armazenado no banco de dados.

    Returns:
        True se a senha bate com o hash, False caso contrário.
    """

    return pwd_context.verify(senha, hash)


def criar_access_token(data: dict) -> str:
    """Cria um token JWT de acesso.

    Gera um token JWT de acesso com os dados fornecidos e expiração configurada
    (padrão 8 horas). Usado para autenticação em endpoints da API.

    Args:
        data: Dicionário de claims a codificar (ex: {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        String de token JWT de acesso codificado.
    """

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token(data: dict) -> str:
    """Cria um token JWT de refresh.

    Gera um token JWT de refresh com os dados fornecidos e expiração configurada
    (padrão 30 dias). Usado para obter novos tokens de acesso.

    Args:
        data: Dicionário de claims a codificar (ex: {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        String de token JWT de refresh codificado.
    """

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str, expected_type: str = "access") -> dict | None:
    """Decodifica e valida um token JWT.

    Decodifica um token JWT e valida sua assinatura e tipo de token.
    Retorna None se o token for inválido, expirado ou de tipo incorreto.

    Args:
        token: String de token JWT a decodificar.
        expected_type: Tipo esperado de token ("access" ou "refresh").

    Returns:
        Dicionário de payload decodificado se válido, None caso contrário.
    """

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
