"""Schemas Pydantic para autenticação e dados de usuários.

Define estruturas de requisição e resposta para login, registro, refresh de tokens
e leitura de dados de usuários e guarnições.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Requisição de autenticação (login).

    Attributes:
        matricula: Matrícula do agente (1 a 50 caracteres).
        senha: Senha em texto plano (mínimo 6 caracteres).
    """

    matricula: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    """Requisição de registro de novo agente.

    Attributes:
        nome: Nome completo do agente (2 a 200 caracteres).
        matricula: Matrícula do agente (1 a 50 caracteres, único por guarnição).
        senha: Senha em texto plano (mínimo 6 caracteres).
        email: Email do agente (opcional, máximo 200 caracteres).
        guarnicao_id: Identificador da guarnição a que o agente pertence.
    """

    nome: str = Field(..., min_length=2, max_length=200)
    matricula: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=6)
    email: str | None = Field(None, max_length=200)
    guarnicao_id: int


class TokenResponse(BaseModel):
    """Resposta com tokens de acesso e refresh.

    Attributes:
        access_token: Token JWT de acesso (curta duração).
        refresh_token: Token JWT para renovação de acesso (longa duração).
        token_type: Tipo de token (padrão: "bearer").
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Requisição para renovação de token de acesso.

    Attributes:
        refresh_token: Token JWT de refresh válido.
    """

    refresh_token: str


class UsuarioRead(BaseModel):
    """Dados públicos de um usuário (agente).

    Representação de leitura (read) do usuário, sem dados sensíveis como
    a senha. Inclui configuração para conversão automática de ORM models.

    Attributes:
        id: Identificador único do usuário.
        nome: Nome completo do agente.
        matricula: Matrícula do agente.
        email: Email do agente (opcional).
        is_admin: Indica se o agente é administrador.
        guarnicao_id: Identificador da guarnição do agente.
        criado_em: Data e hora de criação do usuário.
    """

    id: int
    nome: str
    matricula: str
    email: str | None = None
    is_admin: bool
    guarnicao_id: int
    criado_em: datetime

    model_config = {"from_attributes": True}


class GuarnicaoRead(BaseModel):
    """Dados públicos de uma guarnição.

    Representação de leitura (read) de uma guarnição/unidade operacional.
    Inclui configuração para conversão automática de ORM models.

    Attributes:
        id: Identificador único da guarnição.
        nome: Nome da guarnição (ex: "1º BPM").
        unidade: Tipo de unidade (ex: "Batalhão").
        codigo: Código interno da guarnição.
    """

    id: int
    nome: str
    unidade: str
    codigo: str

    model_config = {"from_attributes": True}
