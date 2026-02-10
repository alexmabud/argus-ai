from fastapi import HTTPException, status


class NaoEncontradoError(HTTPException):
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{recurso} não encontrado",
        )


class AcessoNegadoError(HTTPException):
    def __init__(self, detail: str = "Acesso negado — recurso de outra guarnição"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class CredenciaisInvalidasError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ConflitoDadosError(HTTPException):
    def __init__(self, detail: str = "Registro já existe"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
