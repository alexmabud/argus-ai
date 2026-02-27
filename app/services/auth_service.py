"""Serviço de autenticação e gerenciamento de tokens.

Implementa lógica pura de autenticação (sem dependências FastAPI), incluindo
registro, login, refresh de tokens e validação de credenciais.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, CredenciaisInvalidasError
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)
from app.models.usuario import Usuario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.audit_service import AuditService


class AuthService:
    """Serviço de autenticação e geração de tokens.

    Implementa a lógica de negócio para autenticação de usuários, incluindo
    registro, login, refresh de tokens e validação de credenciais. NÃO importa
    ou depende de FastAPI, mantendo lógica pura.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de usuários.
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UsuarioRepository(db)
        self.audit = AuditService(db)

    async def register(
        self,
        data: RegisterRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Usuario:
        """Registra um novo agente na guarnição.

        Cria novo usuário com senha hasheada e verificações de duplicação de
        matrícula e email. Registra evento de auditoria da criação.

        Args:
            data: Dados de registro (nome, matrícula, senha, email, guarnicao_id).
            ip_address: Endereço IP da requisição de registro (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Usuario: Objeto do usuário criado com ID atribuído.

        Raises:
            ConflitoDadosError: Se matrícula ou email já estão cadastrados.
        """
        existing = await self.repo.get_by_matricula(data.matricula)
        if existing:
            raise ConflitoDadosError("Matricula ja cadastrada")

        if data.email:
            existing_email = await self.repo.get_by_email(data.email)
            if existing_email:
                raise ConflitoDadosError("Email ja cadastrado")

        usuario = Usuario(
            nome=data.nome,
            matricula=data.matricula,
            senha_hash=hash_senha(data.senha),
            email=data.email,
            guarnicao_id=data.guarnicao_id,
        )

        self.db.add(usuario)
        await self.db.flush()

        await self.audit.log(
            usuario_id=usuario.id,
            acao="CREATE",
            recurso="usuario",
            recurso_id=usuario.id,
            detalhes={"matricula": data.matricula},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return usuario

    async def login(
        self,
        matricula: str,
        senha: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Autentica um agente e gera tokens de acesso.

        Valida as credenciais (matrícula e senha), cria tokens JWT de acesso
        e refresh, e registra o evento de login na auditoria.

        Args:
            matricula: Matrícula do agente.
            senha: Senha em texto plano (será verificada contra o hash).
            ip_address: Endereço IP da requisição de login (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            TokenResponse: Tokens de acesso e refresh, e tipo de token.

        Raises:
            CredenciaisInvalidasError: Se matrícula não existe ou senha é inválida.
        """
        usuario = await self.repo.get_by_matricula(matricula)
        if not usuario or not verificar_senha(senha, usuario.senha_hash):
            raise CredenciaisInvalidasError()

        token_data = {
            "sub": str(usuario.id),
            "guarnicao_id": usuario.guarnicao_id,
        }
        access_token = criar_access_token(token_data)
        refresh_token = criar_refresh_token(token_data)

        await self.audit.log(
            usuario_id=usuario.id,
            acao="LOGIN",
            recurso="auth",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Renova os tokens de acesso usando um refresh token válido.

        Decodifica o refresh token, valida o usuário e gera novos tokens
        de acesso e refresh.

        Args:
            refresh_token: Refresh token JWT válido.

        Returns:
            TokenResponse: Novos tokens de acesso e refresh.

        Raises:
            CredenciaisInvalidasError: Se o refresh token é inválido ou o
                usuário não existe ou está inativo.

        Note:
            O refresh token deve conter um payload com 'sub' (user_id) válido
            e ser do tipo 'refresh'.
        """
        payload = decodificar_token(refresh_token, expected_type="refresh")
        if payload is None:
            raise CredenciaisInvalidasError()

        user_id = payload.get("sub")
        if not user_id:
            raise CredenciaisInvalidasError()
        usuario = await self.repo.get(int(user_id))
        if not usuario or not usuario.ativo:
            raise CredenciaisInvalidasError()

        token_data = {
            "sub": str(usuario.id),
            "guarnicao_id": usuario.guarnicao_id,
        }

        return TokenResponse(
            access_token=criar_access_token(token_data),
            refresh_token=criar_refresh_token(token_data),
        )
