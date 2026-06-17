"""Serviço de gerenciamento de usuários pelo administrador.

Implementa criação de usuários com senha de uso único, pausa/reativação
de acesso e geração de novas senhas. Sem dependências FastAPI.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.core.permissions import assert_scope
from app.core.security import hash_senha
from app.models.usuario import Usuario
from app.repositories.usuario_repo import UsuarioRepository
from app.services import notification_service
from app.services.audit_service import AuditService


def _gerar_senha() -> str:
    """Gera senha aleatória segura com entropia mínima de 12 caracteres.

    Usa secrets.token_urlsafe(12) que produz ≈16 chars URL-safe (base64),
    sem truncar, para garantir entropia criptográfica adequada.

    Returns:
        Senha em texto plano com ≥12 caracteres URL-safe.
    """
    return secrets.token_urlsafe(12)


class UsuarioAdminService:
    """Serviço de gestão de usuários para uso exclusivo do administrador.

    Implementa criação com senha única, pausa de acesso (desconecta imediatamente
    via limpeza do session_id), reativação e geração de novas senhas.
    Registra todas as ações via AuditService (LGPD).

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de usuários.
        audit: Serviço de auditoria.
    """

    #: Toggles granulares aceitos no painel de admins.
    _TOGGLES = (
        "pode_criar_usuario",
        "pode_gerar_senha",
        "pode_pausar",
        "pode_mover_equipe",
        "pode_gerir_equipes",
        "admin_global",
    )

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = UsuarioRepository(db)
        self.audit = AuditService(db)

    async def definir_super_admin(self, matricula: str) -> bool:
        """Marca um usuário como super-admin (dono) pela matrícula.

        Operação de bootstrap idempotente e NÃO destrutiva, pensada para rodar
        no deploy (não há endpoint que exponha isto — super-admin nunca é
        delegável pela UI).

        Args:
            matricula: Matrícula do usuário a tornar super-admin.

        Returns:
            True se o usuário existe e ficou marcado como super-admin.

        Raises:
            NaoEncontradoError: Se a matrícula não existir.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.matricula == matricula))
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")
        usuario.is_super_admin = True
        await self.db.flush()
        await self.audit.log(
            usuario_id=usuario.id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario.id,
            detalhes={"acao": "definir_super_admin"},
        )
        return True

    async def listar_admins(self) -> list[Usuario]:
        """Lista admins (super-admins e delegados), ordenados por nome.

        Returns:
            Usuários ativos com is_super_admin OU is_admin.
        """
        result = await self.db.execute(
            select(Usuario)
            .where(
                Usuario.ativo == True,  # noqa: E712
                (Usuario.is_super_admin == True) | (Usuario.is_admin == True),  # noqa: E712
            )
            .order_by(Usuario.nome)
        )
        return list(result.scalars().all())

    async def definir_admin(self, usuario_id: int, flags: dict, admin: Usuario) -> Usuario:
        """Define status de admin delegado e permissões granulares de um usuário.

        Idempotente: promove, edita toggles ou rebaixa. NÃO altera guarnicao_id.
        Com is_admin=False, zera todos os toggles. Bloqueia o super-admin de
        rebaixar a si mesmo (anti-lockout).

        Args:
            usuario_id: ID do usuário alvo.
            flags: Dict com is_admin e os toggles (chaves de _TOGGLES).
            admin: Super-admin autenticado que executa a ação.

        Returns:
            Usuario atualizado.

        Raises:
            NaoEncontradoError: Se o usuário não existir.
            AcessoNegadoError: Se o super-admin tentar rebaixar a si mesmo.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        if not usuario or not usuario.ativo:
            raise NaoEncontradoError("Usuário não encontrado")

        novo_is_admin = bool(flags.get("is_admin", False))

        if usuario.id == admin.id and not novo_is_admin:
            raise AcessoNegadoError("Super-admin não pode rebaixar a si mesmo")

        usuario.is_admin = novo_is_admin
        if not novo_is_admin:
            for toggle in self._TOGGLES:
                setattr(usuario, toggle, False)
        else:
            for toggle in self._TOGGLES:
                setattr(usuario, toggle, bool(flags.get(toggle, False)))

        await self.db.flush()
        await self.audit.log(
            usuario_id=admin.id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario.id,
            detalhes={"acao": "definir_admin", "is_admin": novo_is_admin},
        )
        return usuario

    async def listar_usuarios(self, guarnicao_id: int) -> list[Usuario]:
        """Lista usuários ativos de uma guarnição específica (legado).

        Mantido para compatibilidade. Prefira listar_todos() para o painel admin.

        Args:
            guarnicao_id: ID da guarnição para filtrar usuários.

        Returns:
            Lista de objetos Usuario ordenada por nome.
        """
        result = await self.db.execute(
            select(Usuario)
            .where(Usuario.guarnicao_id == guarnicao_id, Usuario.ativo == True)  # noqa: E712
            .order_by(Usuario.nome)
        )
        return list(result.scalars().all())

    async def listar_todos(self) -> list[Usuario]:
        """Lista todos os usuários ativos do sistema (todas equipes + sem equipe).

        Usado pelo admin para gerenciar usuários globalmente. O frontend
        agrupa por guarnicao_id (incluindo None = "Sem Equipe").

        Returns:
            Lista de Usuario com ativo=True, ordenada por nome.
        """
        result = await self.db.execute(
            select(Usuario)
            .where(Usuario.ativo == True)  # noqa: E712
            .order_by(Usuario.nome)
        )
        return list(result.scalars().all())

    async def criar_usuario(
        self,
        matricula: str,
        admin: Usuario,
        guarnicao_id: int | None = None,
    ) -> tuple[Usuario, str]:
        """Cria novo usuário com senha de uso único gerada automaticamente.

        A senha gerada é retornada em plain text UMA ÚNICA VEZ e deve ser
        exibida imediatamente ao admin. Após o primeiro login do usuário,
        a senha é invalidada automaticamente pelo AuthService.

        Args:
            matricula: Matrícula do novo agente (deve ser única).
            admin: Admin autenticado que está criando (auditoria + scope).
            guarnicao_id: ID da guarnição do novo usuário.

        Returns:
            Tupla (Usuario, senha_plain_text) — senha exibida uma vez.

        Raises:
            ConflitoDadosError: Se matrícula já cadastrada.
            AcessoNegadoError: Se a guarnição-destino estiver fora do alcance do admin.
        """
        if guarnicao_id is not None:
            assert_scope(admin, guarnicao_id)
        admin_id = admin.id
        result = await self.db.execute(select(Usuario).where(Usuario.matricula == matricula))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.ativo:
                raise ConflitoDadosError("Matrícula já cadastrada")
            # usuário inativo (excluído) — reativa e gera nova senha
            senha = _gerar_senha()
            existing.senha_hash = hash_senha(senha)
            existing.ativo = True
            existing.session_id = None
            existing.desativado_em = None
            existing.desativado_por_id = None
            existing.senha_expira_em = datetime.now(UTC) + timedelta(
                hours=settings.SENHA_PROVISORIA_EXPIRE_HOURS
            )
            if guarnicao_id is not None:
                existing.guarnicao_id = guarnicao_id
            await self.db.flush()
            await self.audit.log(
                usuario_id=admin_id,
                acao="UPDATE",
                recurso="usuario",
                recurso_id=existing.id,
                detalhes={"matricula": matricula, "acao": "reativado", "reativado_por": admin_id},
            )
            return existing, senha

        senha = _gerar_senha()
        usuario = Usuario(
            nome=matricula,  # nome provisório até o usuário atualizar o perfil
            matricula=matricula,
            senha_hash=hash_senha(senha),
            guarnicao_id=guarnicao_id,
            session_id=None,  # sem sessão até o primeiro login
            senha_expira_em=datetime.now(UTC)
            + timedelta(hours=settings.SENHA_PROVISORIA_EXPIRE_HOURS),
        )
        self.db.add(usuario)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="usuario",
            recurso_id=usuario.id,
            detalhes={"matricula": matricula, "criado_por": admin_id},
        )

        return usuario, senha

    async def pausar_usuario(self, usuario_id: int, admin: Usuario) -> Usuario:
        """Pausa o acesso do usuário limpando o session_id.

        A limpeza do session_id garante desconexão imediata: qualquer token
        JWT ativo será rejeitado na próxima requisição pelo get_current_user.

        Args:
            usuario_id: ID do usuário a pausar.
            admin: Admin autenticado (auditoria + scope).

        Returns:
            Usuario pausado.

        Raises:
            NaoEncontradoError: Se usuário não existe ou já foi excluído.
            AcessoNegadoError: Se o alvo estiver fora do alcance do admin.
        """
        usuario = await self.repo.get(usuario_id)
        if not usuario or not usuario.ativo:
            raise NaoEncontradoError("Usuário não encontrado")

        assert_scope(admin, usuario.guarnicao_id)
        admin_id = admin.id
        usuario.session_id = None
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "pausar", "admin_id": admin_id},
        )
        await notification_service.alerta_sessao_revogada(usuario.matricula, admin_id)

        return usuario

    async def gerar_nova_senha(self, usuario_id: int, admin: Usuario) -> tuple[str, str]:
        """Gera nova senha de uso único para o usuário, invalidando a sessão atual.

        Limpa session_id (desconecta imediatamente se havia sessão ativa),
        define nova senha de uso único, e reativa o usuário se estava pausado.

        Args:
            usuario_id: ID do usuário.
            admin: Admin autenticado (auditoria + scope).

        Returns:
            Tupla (senha_plain_text, matricula) — exibir senha UMA vez.

        Raises:
            NaoEncontradoError: Se usuário não existe.
            AcessoNegadoError: Se o alvo estiver fora do alcance do admin.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        assert_scope(admin, usuario.guarnicao_id)
        admin_id = admin.id
        senha = _gerar_senha()
        usuario.senha_hash = hash_senha(senha)
        usuario.session_id = None  # desconectar sessão atual
        usuario.ativo = True  # reativar se estava pausado
        usuario.senha_expira_em = datetime.now(UTC) + timedelta(
            hours=settings.SENHA_PROVISORIA_EXPIRE_HOURS
        )

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "gerar_senha", "admin_id": admin_id},
        )

        return senha, usuario.matricula

    async def excluir_usuario(self, usuario_id: int, admin_id: int) -> None:
        """Exclui logicamente o usuário (soft delete — dados preservados por LGPD).

        Marca como inativo e limpa session_id. Dados preservados conforme LGPD.

        Args:
            usuario_id: ID do usuário a excluir.
            admin_id: ID do admin (para auditoria).

        Raises:
            NaoEncontradoError: Se usuário não existe.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        usuario.ativo = False
        usuario.session_id = None
        usuario.desativado_em = datetime.now(UTC)
        usuario.desativado_por_id = admin_id

        await self.audit.log(
            usuario_id=admin_id,
            acao="DELETE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"admin_id": admin_id},
        )

    async def mover_equipe(
        self,
        usuario_id: int,
        guarnicao_id_destino: int | None,
        admin: Usuario,
    ) -> Usuario:
        """Move o usuário para outra equipe ou remove da equipe atual.

        Atualiza guarnicao_id do usuário. Destino None coloca o usuário na
        aba "Sem Equipe" no painel admin, sem invalidar a sessão.

        Args:
            usuario_id: ID do usuário a mover.
            guarnicao_id_destino: ID da equipe de destino, ou None para remover.
            admin: Admin autenticado (auditoria + scope).

        Returns:
            Usuario com guarnicao_id atualizado.

        Raises:
            NaoEncontradoError: Se usuário não existe.
            AcessoNegadoError: Se origem ou destino estiverem fora do alcance do admin.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        assert_scope(admin, usuario.guarnicao_id)  # origem
        assert_scope(admin, guarnicao_id_destino)  # destino
        admin_id = admin.id
        usuario.guarnicao_id = guarnicao_id_destino
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "mover_equipe", "guarnicao_id_destino": guarnicao_id_destino},
        )

        return usuario
