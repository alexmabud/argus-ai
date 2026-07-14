"""Schemas Pydantic para autenticação e dados de usuários.

Define estruturas de requisição e resposta para login, registro, refresh de tokens
e leitura de dados de usuários e guarnições.
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.models.usuario import POSTOS_GRADUACAO
from app.schemas.bpm import BpmRead
from app.schemas.validators import UpperStr, UpperStrReq
from app.services.storage_service import normalize_storage_url

#: Restringe foto_url a chaves geradas pelo próprio servidor em
#: StorageService.generate_key("avatares", ...) — /storage/{bucket}/avatares/{key},
#: sem subpaths. Impede que o usuário aponte o próprio avatar para qualquer outro
#: objeto do bucket (PDFs, fotos de outra pessoa, objetos órfãos).
_AVATAR_PATH_RE = re.compile(rf"^/storage/{re.escape(settings.S3_BUCKET)}/avatares/[^/]+$")


class LoginRequest(BaseModel):
    """Requisição de autenticação (login).

    Attributes:
        matricula: Matrícula do agente (1 a 50 caracteres, alfanumérico + ._-).
        senha: Senha em texto plano (mínimo 6 caracteres).
        totp_code: Código TOTP de 6 dígitos (obrigatório para admins com 2FA ativo).
    """

    matricula: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    senha: str = Field(..., min_length=6)
    totp_code: str | None = Field(None, min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    """Par de tokens JWT de acesso e refresh — uso interno (service → router).

    NUNCA retornado diretamente como corpo de resposta HTTP: o router usa os
    valores para popular os cookies HttpOnly (``set_access_cookie``/
    ``set_refresh_cookie``) e devolve ``AuthSuccessResponse`` ao cliente.
    Ver achado #13/2026-07-13 — tokens em claro no corpo JSON são legíveis
    por qualquer script da página (XSS) ou extensão de navegador, enquanto
    os cookies já são o canal canônico.

    Attributes:
        access_token: Token JWT de acesso (curta duração).
        refresh_token: Token JWT para renovação de acesso (longa duração).
        token_type: Tipo de token (padrão: "bearer").
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthSuccessResponse(BaseModel):
    """Confirmação de login/refresh bem-sucedido — sem tokens no corpo.

    Os tokens JWT são entregues exclusivamente via cookies HttpOnly
    (``Set-Cookie`` na resposta); o corpo JSON não carrega nenhum segredo.

    Attributes:
        autenticado: Sempre True — a própria resposta 200 já confirma.
    """

    autenticado: bool = True


class RefreshRequest(BaseModel):
    """Requisição para renovação de token de acesso.

    Durante a transição para cookie HttpOnly, refresh_token no corpo é
    opcional — o backend prefere o cookie argus_refresh_token quando presente.

    Attributes:
        refresh_token: Token JWT de refresh válido (opcional — fallback ao corpo).
    """

    refresh_token: str | None = None


class UsuarioRead(BaseModel):
    """Dados públicos de um usuário (agente).

    Representação de leitura (read) do usuário, sem dados sensíveis como
    a senha. Inclui configuração para conversão automática de ORM models.

    Attributes:
        id: Identificador único do usuário.
        nome: Nome completo do agente.
        matricula: Matrícula do agente.
        email: Email do agente (opcional).
        is_admin: Indica se o agente é admin delegado.
        is_super_admin: Indica se o agente é o super-admin (dono).
        pode_criar_usuario: Permissão granular — criar usuários.
        pode_gerar_senha: Permissão granular — gerar nova senha.
        pode_pausar: Permissão granular — pausar usuários.
        pode_mover_equipe: Permissão granular — mover usuários entre equipes.
        pode_gerir_equipes: Permissão granular — criar/editar equipes e BPMs.
        admin_global: Alcance do admin delegado (True = todas as equipes).
        totp_ativo: Indica se o 2FA TOTP está configurado (True = secret salvo no banco).
        guarnicao_id: Identificador da guarnição do agente.
        posto_graduacao: Posto ou graduação PM (ex: "Sargento").
        nome_guerra: Nome de guerra do agente (ex: "Silva").
        foto_url: URL pública da foto de perfil no storage S3-compatible.
        criado_em: Data e hora de criação do usuário.
    """

    id: int
    nome: str
    matricula: str
    email: str | None = None
    is_admin: bool
    is_super_admin: bool = False
    pode_criar_usuario: bool = False
    pode_gerar_senha: bool = False
    pode_pausar: bool = False
    pode_mover_equipe: bool = False
    pode_gerir_equipes: bool = False
    admin_global: bool = False
    totp_ativo: bool = False
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
        foto_url: URL pública da foto de perfil no storage S3-compatible (opcional).
    """

    nome: UpperStrReq = Field(..., min_length=2, max_length=200)
    nome_guerra: UpperStr = Field(None, max_length=50)
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
        """Restringe foto_url a chaves de avatar geradas pelo servidor.

        Bloqueia URLs externas (policial poderia gravar uma URL de atacante
        no perfil — outros usuarios que abrirem a ficha pingariam o servidor
        exfiltrando IP + referer) E bloqueia apontar o avatar para qualquer
        outro objeto do bucket (PDF de ocorrência, foto de outra pessoa,
        objeto órfão) — só aceita o padrão /storage/{bucket}/avatares/{key}
        que POST /perfil/foto realmente gera.

        Args:
            v: Valor de foto_url a validar.

        Returns:
            O valor se valido, None se nao fornecido.

        Raises:
            ValueError: Se foto_url não apontar para uma chave de avatar.
        """
        if v is not None and not _AVATAR_PATH_RE.match(v):
            raise ValueError("foto_url deve apontar para um avatar gerado pelo servidor")
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

    matricula: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
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
        is_admin: Indica se é admin delegado.
        is_super_admin: Indica se é o super-admin (dono).
        pode_criar_usuario: Permissão granular — criar usuários.
        pode_gerar_senha: Permissão granular — gerar nova senha.
        pode_pausar: Permissão granular — pausar usuários.
        pode_mover_equipe: Permissão granular — mover usuários entre equipes.
        pode_gerir_equipes: Permissão granular — criar/editar equipes e BPMs.
        admin_global: Alcance do admin delegado (True = todas as equipes).
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
    is_super_admin: bool = False
    pode_criar_usuario: bool = False
    pode_gerar_senha: bool = False
    pode_pausar: bool = False
    pode_mover_equipe: bool = False
    pode_gerir_equipes: bool = False
    admin_global: bool = False
    ativo: bool
    tem_sessao: bool
    guarnicao_id: int | None = None

    _normalize_foto = field_validator("foto_url", mode="before")(normalize_storage_url)

    model_config = {"from_attributes": True}


class AdminPermissoesUpdate(BaseModel):
    """Define status de admin e permissões granulares (entrada do super-admin).

    Idempotente: serve para promover, editar toggles e rebaixar. Com
    is_admin=False, o backend zera todos os toggles. Excluir usuário e
    promover admin NÃO entram aqui (são exclusivos do super-admin).

    Attributes:
        is_admin: True torna/mantém admin delegado; False rebaixa.
        pode_criar_usuario: Pode criar novos usuários.
        pode_gerar_senha: Pode gerar nova senha de uso único.
        pode_pausar: Pode pausar (desconectar) usuários.
        pode_mover_equipe: Pode mover usuários entre equipes.
        pode_gerir_equipes: Pode criar/editar equipes e BPMs (requer admin_global).
        admin_global: Alcance — True todas as equipes, False só a própria.
    """

    is_admin: bool = False
    pode_criar_usuario: bool = False
    pode_gerar_senha: bool = False
    pode_pausar: bool = False
    pode_mover_equipe: bool = False
    pode_gerir_equipes: bool = False
    admin_global: bool = False


class AdminRead(BaseModel):
    """Dados de um admin para a página de admins (saída).

    Attributes:
        id: ID do usuário.
        nome: Nome do agente.
        matricula: Matrícula.
        guarnicao_id: Equipe atual (mantida ao promover). None = sem equipe.
        is_super_admin: Indica o dono.
        is_admin: Indica admin delegado.
        pode_criar_usuario: Toggle — criar usuários.
        pode_gerar_senha: Toggle — gerar nova senha.
        pode_pausar: Toggle — pausar usuários.
        pode_mover_equipe: Toggle — mover entre equipes.
        pode_gerir_equipes: Toggle — gerir equipes/BPMs.
        admin_global: Alcance do admin delegado.
    """

    id: int
    nome: str
    matricula: str
    guarnicao_id: int | None = None
    is_super_admin: bool
    is_admin: bool
    pode_criar_usuario: bool
    pode_gerar_senha: bool
    pode_pausar: bool
    pode_mover_equipe: bool
    pode_gerir_equipes: bool
    admin_global: bool

    model_config = {"from_attributes": True}
