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
    """Serviço de autenticação. NÃO importa FastAPI."""

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
        payload = decodificar_token(refresh_token, expected_type="refresh")
        if payload is None:
            raise CredenciaisInvalidasError()

        user_id = payload.get("sub")
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
