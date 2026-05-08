"""Helpers para autenticação via cookie HTTPOnly.

Permite que requisições de browser que não conseguem enviar o header
``Authorization: Bearer ...`` automaticamente — como ``<img src>``,
``<video>`` e ``<a download>`` — autentiquem-se via cookie. O cookie
é HTTPOnly (imune a roubo via XSS), Secure (só HTTPS) e SameSite=Strict
(imune a CSRF).

Em paralelo ao cookie, o frontend continua armazenando o token em
localStorage para uso explícito via ``fetch`` com header Bearer; ambos
caminhos são aceitos por ``get_current_user`` no backend.
"""

from fastapi import Response

from app.config import settings

#: Nome do cookie que carrega o access token JWT. Lido como fallback
#: pelo ``get_current_user`` quando o header Authorization está ausente.
ACCESS_TOKEN_COOKIE = "argus_access_token"


def set_access_cookie(response: Response, token: str) -> None:
    """Seta o cookie HTTPOnly com o access token JWT.

    Args:
        response: Resposta FastAPI/Starlette que terá o cookie anexado.
        token: Access token JWT a armazenar.
    """
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="strict",
        path="/",
    )


def clear_access_cookie(response: Response) -> None:
    """Remove o cookie de access token (logout / fim de sessão).

    Args:
        response: Resposta FastAPI/Starlette que terá o cookie removido.
    """
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        secure=not settings.DEBUG,
        samesite="strict",
    )
