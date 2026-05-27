"""Utilitários de segurança para hashing de senhas e geração de tokens JWT.

Fornece funções para hashing de senhas com bcrypt, verificação de credenciais
e criação/validação de tokens JWT para fluxos de autenticação e autorização.
"""

import logging
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger("argus")

#: Custo bcrypt (rounds). 12 = ~250ms/hash em CPU moderno — balanco entre
#: defesa contra brute-force e UX de login (mantido do passlib).
_BCRYPT_ROUNDS = 12


def _truncar_bcrypt(senha: str) -> bytes:
    """Trunca senha para 72 bytes (limite do algoritmo bcrypt).

    O bcrypt rejeita senhas > 72 bytes desde a versao 4.1+ (em vez de
    truncar silenciosamente). Esta funcao garante compatibilidade.

    Args:
        senha: Senha em texto plano.

    Returns:
        Senha truncada para no maximo 72 bytes UTF-8.
    """
    return senha.encode("utf-8")[:72]


def hash_senha(senha: str) -> str:
    """Faz hash de uma senha usando bcrypt.

    Args:
        senha: Senha em texto plano a ser hasheada.

    Returns:
        String de hash bcrypt adequada para armazenamento em banco de dados.
    """
    return bcrypt.hashpw(_truncar_bcrypt(senha), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(
        "utf-8"
    )


def verificar_senha(senha: str, hash: str) -> bool:
    """Verifica uma senha em texto plano contra um hash bcrypt.

    Retorna False (em vez de lancar excecao) se o hash armazenado estiver
    corrompido ou em formato nao reconhecido, evitando erros 500. Aceita
    tanto hashes com prefixo $2b$ (atual) quanto $2a$ (legados do passlib).

    Args:
        senha: Senha em texto plano a verificar.
        hash: Hash bcrypt armazenado no banco de dados.

    Returns:
        True se a senha bate com o hash, False caso contrario ou se hash invalido.
    """
    try:
        return bcrypt.checkpw(_truncar_bcrypt(senha), hash.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        logger.warning("hash bcrypt invalido: %s", exc)
        return False


#: Issuer e audience padrão para tokens JWT do Argus AI.
_JWT_ISSUER = "argus-ai"
_JWT_AUDIENCE = "argus-api"


def criar_access_token(data: dict) -> str:
    """Cria um token JWT de acesso.

    Gera um token JWT de acesso com os dados fornecidos e expiração configurada
    (padrão 8 horas). Inclui claims iss e aud para evitar replay entre serviços.

    Args:
        data: Dicionário de claims a codificar (ex: {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        String de token JWT de acesso codificado.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "iss": _JWT_ISSUER,
            "aud": _JWT_AUDIENCE,
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token(data: dict) -> str:
    """Cria um token JWT de refresh.

    Gera um token JWT de refresh com os dados fornecidos e expiração configurada
    (padrão 30 dias). Inclui claims iss e aud para evitar replay entre serviços.

    Args:
        data: Dicionário de claims a codificar (ex: {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        String de token JWT de refresh codificado.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "iss": _JWT_ISSUER,
            "aud": _JWT_AUDIENCE,
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str, expected_type: str = "access") -> dict | None:
    """Decodifica e valida um token JWT.

    Decodifica um token JWT e valida assinatura, tipo, issuer e audience.
    Retorna None se o token for inválido, expirado ou de tipo incorreto.

    Args:
        token: String de token JWT a decodificar.
        expected_type: Tipo esperado de token ("access" ou "refresh").

    Returns:
        Dicionário de payload decodificado se válido, None caso contrário.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=_JWT_AUDIENCE,
            issuer=_JWT_ISSUER,
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.InvalidTokenError:
        return None
