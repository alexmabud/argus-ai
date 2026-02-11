from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    matricula: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    matricula: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=6)
    email: str | None = Field(None, max_length=200)
    guarnicao_id: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UsuarioRead(BaseModel):
    id: int
    nome: str
    matricula: str
    email: str | None = None
    is_admin: bool
    guarnicao_id: int
    criado_em: datetime

    model_config = {"from_attributes": True}


class GuarnicaoRead(BaseModel):
    id: int
    nome: str
    unidade: str
    codigo: str

    model_config = {"from_attributes": True}
