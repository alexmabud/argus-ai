"""Serviço de gerenciamento de usuários pelo administrador.

Implementa criação de usuários com senha de uso único, pausa/reativação
de acesso e geração de novas senhas. Sem dependências FastAPI.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.security import hash_senha
from app.models.usuario import Usuario
from app.repositories.usuario_repo import UsuarioRepository
from app.services.audit_service import AuditService


def _gerar_senha() -> str:
    """Gera senha aleatória segura de 10 caracteres.

    Usa secrets.token_urlsafe para garantir aleatoriedade criptográfica.

    Returns:
        Senha em texto plano com 10 caracteres URL-safe.
    """
    return secrets.token_urlsafe(8)[:10]


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

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = UsuarioRepository(db)
        self.audit = AuditService(db)

    async def listar_usuarios(self, guarnicao_id: int) -> list[Usuario]:
        """Lista todos os usuários ativos e pausados da guarnição.

        Retorna usuários com ativo=True. Excluídos (ativo=False) são omitidos.

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

    async def criar_usuario(
        self,
        matricula: str,
        admin_id: int,
        guarnicao_id: int | None = None,
    ) -> tuple[Usuario, str]:
        """Cria novo usuário com senha de uso único gerada automaticamente.

        A senha gerada é retornada em plain text UMA ÚNICA VEZ e deve ser
        exibida imediatamente ao admin. Após o primeiro login do usuário,
        a senha é invalidada automaticamente pelo AuthService.

        Args:
            matricula: Matrícula do novo agente (deve ser única).
            admin_id: ID do admin que está criando (para auditoria).
            guarnicao_id: ID da guarnição do novo usuário.

        Returns:
            Tupla (Usuario, senha_plain_text) — senha exibida uma vez.

        Raises:
            ConflitoDadosError: Se matrícula já cadastrada.
        """
        existing = await self.repo.get_by_matricula(matricula)
        if existing:
            raise ConflitoDadosError("Matrícula já cadastrada")

        senha = _gerar_senha()
        usuario = Usuario(
            nome=matricula,  # nome provisório até o usuário atualizar o perfil
            matricula=matricula,
            senha_hash=hash_senha(senha),
            guarnicao_id=guarnicao_id,
            session_id=None,  # sem sessão até o primeiro login
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

    async def pausar_usuario(self, usuario_id: int, admin_id: int) -> Usuario:
        """Pausa o acesso do usuário limpando o session_id.

        A limpeza do session_id garante desconexão imediata: qualquer token
        JWT ativo será rejeitado na próxima requisição pelo get_current_user.

        Args:
            usuario_id: ID do usuário a pausar.
            admin_id: ID do admin (para auditoria).

        Returns:
            Usuario pausado.

        Raises:
            NaoEncontradoError: Se usuário não existe ou já foi excluído.
        """
        usuario = await self.repo.get(usuario_id)
        if not usuario or not usuario.ativo:
            raise NaoEncontradoError("Usuário não encontrado")

        usuario.session_id = None

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "pausar", "admin_id": admin_id},
        )

        return usuario

    async def gerar_nova_senha(self, usuario_id: int, admin_id: int) -> str:
        """Gera nova senha de uso único para o usuário, invalidando a sessão atual.

        Limpa session_id (desconecta imediatamente se havia sessão ativa),
        define nova senha de uso único, e reativa o usuário se estava pausado.

        Args:
            usuario_id: ID do usuário.
            admin_id: ID do admin (para auditoria).

        Returns:
            Nova senha em plain text — exibir UMA vez.

        Raises:
            NaoEncontradoError: Se usuário não existe.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = await result.scalar_one_or_none()  # type: ignore[misc]
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        senha = _gerar_senha()
        usuario.senha_hash = hash_senha(senha)
        usuario.session_id = None  # desconectar sessão atual
        usuario.ativo = True  # reativar se estava pausado

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "gerar_senha", "admin_id": admin_id},
        )

        return senha

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
