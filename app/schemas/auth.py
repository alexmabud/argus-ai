"""Schemas Pydantic para autenticação e dados de usuários.

Define estruturas de requisição e resposta para login, registro, refresh de tokens
e leitura de dados de usuários e guarnições.
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.usuario import POSTOS_GRADUACAO
from app.schemas.bpm import BpmRead
from app.services.storage_service import normalize_storage_url

#: Regex para validação de complexidade de senha.
_SENHA_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def _validar_complexidade_senha(v: str) -> str:
    """Valida complexidade de senha: 8+ chars, maiúscula, minúscula, dígito, especial.

    Args:
        v: Senha a validar.

    Returns:
        Senha validada.

    Raises:
        ValueError: Se senha não atender requisitos de complexidade.
    """
    if not _SENHA_PATTERN.match(v):
        raise ValueError(
            "Senha deve ter no mínimo 8 caracteres, incluindo: "
            "1 maiúscula, 1 minúscula, 1 dígito e 1 caractere especial"
        )
    return v


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
        matricula: Matrícula do agente (1 a 50 caracteres, único no sistema).
        senha: Senha em texto plano (mínimo 8 chars com complexidade).
        email: Email do agente (opcional, máximo 200 caracteres).
    """

    nome: str = Field(..., min_length=2, max_length=200)
    matricula: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=8)
    email: str | None = Field(None, max_length=200)

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        """Valida complexidade de senha no registro.

        Args:
            v: Senha a validar.

        Returns:
            Senha validada.

        Raises:
            ValueError: Se senha não atender complexidade.
        """
        return _validar_complexidade_senha(v)


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
        posto_graduacao: Posto ou graduação PM (ex: "Sargento").
        nome_guerra: Nome de guerra do agente (ex: "Silva").
        foto_url: URL pública da foto de perfil no R2.
        criado_em: Data e hora de criação do usuário.
    """

    id: int
    nome: str
    matricula: str
    email: str | None = None
    is_admin: bool
    guarnicao_id: int | None = None
    posto_graduacao: str | None = None
    nome_guerra: str | None = None
    foto_url: str | None = None
    criado_em: datetime

    _normalize_foto = field_validator("foto_url", mode="before")(normalize_storage_url)

    model_config = {"from_attributes": True}


class UsuarioResumoRead(BaseModel):
    """Dados mínimos de usuário para exibição em cards de abordagem.

    Versão compacta de UsuarioRead com apenas os campos necessários
    para identificar o policial em listas e relatórios.

    Attributes:
        id: Identificador único do usuário.
        posto_graduacao: Posto ou graduação abreviado (ex: "SD", "CB", "3SGT").
        nome_guerra: Nome de guerra do agente (ex: "Silva").
    """

    id: int
    posto_graduacao: str | None = None
    nome_guerra: str | None = None

    model_config = {"from_attributes": True}


class GuarnicaoRead(BaseModel):
    """Dados públicos de uma guarnição (Equipe).

    Representação de leitura. A UI exibe como "Equipe" — internamente
    a entidade chama-se "guarnicao". Inclui o BPM pai e o campo
    isolamento_abordagens para controle de visibilidade de abordagens.

    Attributes:
        id: Identificador único da guarnição.
        nome: Nome da equipe (ex: "3ª Cia - GU 01").
        bpm_id: ID do BPM ao qual pertence.
        bpm: Dados do BPM pai (carregado via selectin).
        codigo: Código interno único.
        isolamento_abordagens: Se True, membros veem apenas as abordagens
            da própria equipe. Se False (padrão), veem todas.
    """

    id: int
    nome: str
    bpm_id: int
    bpm: BpmRead
    codigo: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}


# Alias semântico — Equipe = Guarnicao. UI usa "Equipe", código usa "guarnicao".
EquipeRead = GuarnicaoRead


class EquipeCreate(BaseModel):
    """Dados para criação de nova equipe (guarnição) pelo admin.

    O código é gerado automaticamente pelo serviço a partir do nome e BPM.

    Attributes:
        nome: Nome descritivo da equipe (1-200 caracteres).
        bpm_id: ID do BPM ao qual a equipe pertencerá.
    """

    nome: str = Field(..., min_length=1, max_length=200)
    bpm_id: int = Field(..., ge=1)


class EquipeIsolamentoUpdate(BaseModel):
    """Dados para alternar isolamento de abordagens de uma equipe.

    Attributes:
        isolamento_abordagens: True ativa isolamento, False desativa.
    """

    isolamento_abordagens: bool


class UsuarioMoverEquipe(BaseModel):
    """Dados para mover usuário entre equipes (ou remover de equipe).

    Attributes:
        guarnicao_id: ID da equipe de destino. None remove da equipe
            atual (usuário fica em "Sem Equipe").
    """

    guarnicao_id: int | None = None


class PerfilUpdate(BaseModel):
    """Dados para atualização do perfil do usuário.

    Permite atualizar nome, nome de guerra, posto/graduação e URL da foto.
    O posto_graduacao deve ser um valor da lista POSTOS_GRADUACAO.

    Attributes:
        nome: Nome completo do agente (2 a 200 caracteres).
        nome_guerra: Nome de guerra do agente (ex: "Silva"). Máx 50 chars.
        posto_graduacao: Posto ou graduação PM (lista fixa). None para remover.
        foto_url: URL pública da foto de perfil no R2 (opcional).
    """

    nome: str = Field(..., min_length=2, max_length=200)
    nome_guerra: str | None = Field(None, max_length=50)
    posto_graduacao: str | None = Field(None, max_length=50)
    foto_url: str | None = Field(None, max_length=500)

    @field_validator("posto_graduacao")
    @classmethod
    def validar_posto(cls, v: str | None) -> str | None:
        """Valida que o posto é da lista oficial PM.

        Args:
            v: Valor do posto a validar.

        Returns:
            O valor do posto se válido, None se não fornecido.

        Raises:
            ValueError: Se posto não estiver na lista POSTOS_GRADUACAO.
        """
        if v is not None and v not in POSTOS_GRADUACAO:
            raise ValueError(f"Posto inválido. Valores aceitos: {POSTOS_GRADUACAO}")
        return v

    @field_validator("foto_url")
    @classmethod
    def validar_foto_url(cls, v: str | None) -> str | None:
        """Restringe foto_url a paths internos /storage/...

        Bloqueia URLs externas que policial pode gravar no perfil — outros
        usuarios que abrirem a ficha pingariam o servidor do atacante
        exfiltrando IP + referer.

        Args:
            v: Valor de foto_url a validar.

        Returns:
            O valor se valido, None se nao fornecido.

        Raises:
            ValueError: Se foto_url nao comecar com /storage/.
        """
        if v is not None and not v.startswith("/storage/"):
            raise ValueError("foto_url deve ser um path interno /storage/...")
        return v


class UsuarioAdminCreate(BaseModel):
    """Dados para criação de usuário pelo admin.

    O admin informa matrícula e, opcionalmente, a equipe (guarnicao_id).
    O sistema gera a senha automaticamente.

    Attributes:
        matricula: Matrícula do agente (1-50 caracteres, único no sistema).
        guarnicao_id: ID da equipe (opcional). None = "Sem Equipe" —
            admin atribui depois pela aba "Sem Equipe" no painel.
    """

    matricula: str = Field(..., min_length=1, max_length=50)
    guarnicao_id: int | None = Field(None, ge=1)


class SenhaGeradaResponse(BaseModel):
    """Resposta com senha gerada pelo sistema (exibida apenas uma vez).

    Attributes:
        usuario_id: ID do usuário criado ou atualizado.
        matricula: Matrícula do usuário.
        senha: Senha gerada em texto plano — exibir UMA vez e descartar.
    """

    usuario_id: int
    matricula: str
    senha: str


class UsuarioAdminRead(BaseModel):
    """Dados de usuário para listagem no painel admin.

    Attributes:
        id: Identificador único do usuário.
        nome: Nome completo do agente.
        matricula: Matrícula do agente.
        posto_graduacao: Posto ou graduação PM.
        nome_guerra: Nome de guerra do agente.
        foto_url: URL da foto de perfil.
        is_admin: Indica se é administrador.
        ativo: Indica se o acesso está ativo.
        tem_sessao: Indica se há sessão ativa (session_id != None).
        guarnicao_id: ID da guarnição.
    """

    id: int
    nome: str
    matricula: str
    posto_graduacao: str | None = None
    nome_guerra: str | None = None
    foto_url: str | None = None
    is_admin: bool
    ativo: bool
    tem_sessao: bool
    guarnicao_id: int | None = None

    _normalize_foto = field_validator("foto_url", mode="before")(normalize_storage_url)

    model_config = {"from_attributes": True}
