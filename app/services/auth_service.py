"""Serviço de autenticação e gerenciamento de tokens.

Implementa lógica pura de autenticação (sem dependências FastAPI), incluindo
registro, login, refresh de tokens e validação de credenciais.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.core.exceptions import (
    ContaBloqueadaError,
    CredenciaisInvalidasError,
)
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)
from app.models.audit_log import AuditLog
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.auth import TokenResponse
from app.services import notification_service
from app.services.audit_service import AuditService

#: Quantidade de falhas consecutivas que dispara bloqueio temporario.
LIMIAR_BLOQUEIO = 5
#: Duracao do bloqueio temporario apos atingir o limiar.
DURACAO_BLOQUEIO = timedelta(minutes=15)


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

    async def login(
        self,
        matricula: str,
        senha: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        totp_code: str | None = None,
    ) -> TokenResponse:
        """Autentica um agente e gera sessão JWT.

        Comportamento varia conforme o perfil do usuário:
        - **Usuário comum**: senha de uso único (substituída por hash inutilizável
          após o primeiro login) e sessão exclusiva (novo session_id invalida
          tokens anteriores em outros dispositivos).
        - **Admin**: senha permanente reutilizável e session_id estável, permitindo
          sessões simultâneas em múltiplos dispositivos (celular + desktop).

        Args:
            matricula: Matrícula do agente.
            senha: Senha fornecida pelo usuário.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            TokenResponse: Tokens JWT de acesso e refresh com session_id embutido.

        Raises:
            CredenciaisInvalidasError: Se matrícula não existe ou senha é inválida.
        """
        usuario = await self.repo.get_by_matricula(matricula)
        if not usuario:
            raise CredenciaisInvalidasError()

        agora = datetime.now(UTC)
        if usuario.bloqueado_ate and usuario.bloqueado_ate > agora:
            raise ContaBloqueadaError(f"Conta bloqueada ate {usuario.bloqueado_ate.isoformat()}")

        if not verificar_senha(senha, usuario.senha_hash):
            usuario.tentativas_falhas += 1
            if usuario.tentativas_falhas >= LIMIAR_BLOQUEIO:
                usuario.bloqueado_ate = agora + DURACAO_BLOQUEIO
                usuario.tentativas_falhas = 0
            await self.db.flush()
            await self.db.commit()
            raise CredenciaisInvalidasError()

        # Rejeita senha provisória expirada (apenas usuários comuns — admin isento).
        if not usuario.is_admin and usuario.senha_expira_em and usuario.senha_expira_em < agora:
            await self.audit.log(
                usuario_id=usuario.id,
                acao="LOGIN_FAILED",
                recurso="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                detalhes={"motivo": "senha_expirada"},
            )
            raise CredenciaisInvalidasError()

        # Verificar TOTP ANTES de zerar fail counter — evita bypass de lockout:
        # senha correta + TOTP errado não deve resetar tentativas_falhas,
        # pois um atacante com a senha poderia fazer brute-force do TOTP sem bloqueio.
        if usuario.is_admin and usuario.totp_secret:
            if not totp_code:
                raise CredenciaisInvalidasError()
            try:
                secret_plain = decrypt(usuario.totp_secret)
                totp = pyotp.TOTP(secret_plain)
                if not totp.verify(totp_code, valid_window=1):
                    raise CredenciaisInvalidasError()
            except CredenciaisInvalidasError:
                raise
            except Exception:
                raise CredenciaisInvalidasError()

        # Sucesso completo (senha + TOTP): zera contador e libera bloqueio.
        usuario.tentativas_falhas = 0
        usuario.bloqueado_ate = None

        if usuario.is_admin:
            # Admin: senha permanente e sessão compartilhável entre dispositivos.
            # session_id é gerado apenas se ainda não existe; mantido nos demais
            # logins para que tokens de celular e desktop coexistam.
            if usuario.session_id is None:
                usuario.session_id = str(uuid.uuid4())
            novo_session_id = usuario.session_id
        else:
            # Usuário comum: senha de uso único — substituir por hash inutilizável
            usuario.senha_hash = hash_senha(secrets.token_hex(32))
            usuario.senha_expira_em = None  # TTL consumido no primeiro login
            # Sessão exclusiva — novo session_id invalida tokens anteriores
            novo_session_id = str(uuid.uuid4())
            usuario.session_id = novo_session_id

        await self.db.flush()

        token_data: dict = {
            "sub": str(usuario.id),
            "sid": novo_session_id,
        }
        if usuario.guarnicao_id is not None:
            token_data["guarnicao_id"] = usuario.guarnicao_id
        access_token = criar_access_token(token_data)
        refresh_token = criar_refresh_token(token_data)

        await self.audit.log(
            usuario_id=usuario.id,
            acao="LOGIN",
            recurso="auth",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Alerta de IP novo: verificar se o IP já apareceu em LOGINs anteriores.
        if ip_address:
            result = await self.db.execute(
                select(AuditLog)
                .where(
                    AuditLog.usuario_id == usuario.id,
                    AuditLog.acao == "LOGIN",
                    AuditLog.ip_address == ip_address,
                )
                .limit(2)
            )
            historico = result.scalars().all()
            # Se só há 1 registro (o recém-inserido pelo flush acima), é IP novo
            if len(historico) <= 1:
                await notification_service.alerta_login_ip_novo(usuario.matricula, ip_address)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Renova os tokens de acesso mantendo o session_id existente.

        Decodifica o refresh token, valida o usuário e session_id, e gera
        novos tokens mantendo o mesmo session_id (sem rotação de sessão).

        Args:
            refresh_token: Refresh token JWT válido com claim 'sid'.

        Returns:
            TokenResponse: Novos tokens de acesso e refresh.

        Raises:
            CredenciaisInvalidasError: Se refresh token inválido, usuário não existe
                ou session_id não confere.
        """
        payload = decodificar_token(refresh_token, expected_type="refresh")
        if payload is None:
            raise CredenciaisInvalidasError()

        user_id = payload.get("sub")
        sid = payload.get("sid")
        if not user_id:
            raise CredenciaisInvalidasError()

        usuario = await self.repo.get(int(user_id))
        if not usuario or not usuario.ativo:
            raise CredenciaisInvalidasError()

        # Verificar session_id — rejeitar se sessão foi revogada
        if usuario.session_id is None or usuario.session_id != sid:
            raise CredenciaisInvalidasError()

        token_data: dict = {"sub": str(usuario.id), "sid": sid}
        if usuario.guarnicao_id is not None:
            token_data["guarnicao_id"] = usuario.guarnicao_id

        return TokenResponse(
            access_token=criar_access_token(token_data),
            refresh_token=criar_refresh_token(token_data),
        )
