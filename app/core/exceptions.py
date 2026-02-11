"""Exceções customizadas para tratamento de erros da API.

Define exceções HTTP padronizadas para diferentes cenários de erro:
404 (não encontrado), 403 (acesso negado), 401 (credenciais inválidas),
409 (conflito de dados). Todas herdam de HTTPException do FastAPI.
"""

from fastapi import HTTPException, status


class NaoEncontradoError(HTTPException):
    """Exceção para recurso não encontrado (404).

    Levantada quando um recurso solicitado não existe no banco de dados.

    Args:
        recurso: Nome do recurso não encontrado (ex: "Pessoa", "Abordagem").
    """

    def __init__(self, recurso: str = "Recurso"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{recurso} não encontrado",
        )


class AcessoNegadoError(HTTPException):
    """Exceção para acesso negado a recurso (403).

    Levantada quando usuário tenta acessar recurso de outra guarnição ou
    sem permissão apropriada.

    Args:
        detail: Mensagem de erro customizada.
    """

    def __init__(self, detail: str = "Acesso negado — recurso de outra guarnição"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class CredenciaisInvalidasError(HTTPException):
    """Exceção para credenciais inválidas (401).

    Levantada quando falha autenticação (senha errada, token inválido, etc).
    Inclui header WWW-Authenticate obrigatório para autenticação Bearer.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ConflitoDadosError(HTTPException):
    """Exceção para conflito de dados (409).

    Levantada quando ocorre violação de constraint (ex: matrícula duplicada,
    placa já registrada, etc).

    Args:
        detail: Mensagem de erro customizada.
    """

    def __init__(self, detail: str = "Registro já existe"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
