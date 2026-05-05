"""Serviço de gestão de BPMs (Batalhões de Polícia Militar).

Implementa listagem e criação de BPMs. Sem dependências FastAPI.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.bpm import Bpm
from app.services.audit_service import AuditService


class BpmService:
    """Serviço de gestão de BPMs para uso do administrador.

    Cobre listagem e criação de BPMs. Registra mutações via AuditService.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        audit: Serviço de auditoria (LGPD).
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.audit = AuditService(db)

    async def listar_bpms(self) -> list[Bpm]:
        """Lista todos os BPMs ativos, ordenados por nome.

        Returns:
            Lista de Bpm com ativo=True.
        """
        result = await self.db.execute(
            select(Bpm)
            .where(Bpm.ativo == True)  # noqa: E712
            .order_by(Bpm.nome)
        )
        return list(result.scalars().all())

    async def criar_bpm(self, nome: str, admin_id: int) -> Bpm:
        """Cria novo BPM com o nome fornecido.

        Args:
            nome: Nome do BPM (ex: "14º BPM").
            admin_id: ID do admin que está criando (auditoria).

        Returns:
            BPM criado com ID atribuído.

        Raises:
            ConflitoDadosError: Se já existe BPM ativo com o mesmo nome.
        """
        existing = await self.db.execute(
            select(Bpm).where(
                Bpm.nome == nome,
                Bpm.ativo == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise ConflitoDadosError("Já existe um BPM com este nome")

        bpm = Bpm(nome=nome)
        self.db.add(bpm)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="bpm",
            recurso_id=bpm.id,
            detalhes={"nome": nome},
        )
        return bpm

    async def toggle_isolamento(self, bpm_id: int, valor: bool, admin_id: int) -> Bpm:
        """Define o valor de isolamento_abordagens do BPM.

        Quando ativo, usuários do BPM veem apenas abordagens do próprio BPM.
        O isolamento de equipe prevalece se ambos estiverem ativos.

        Args:
            bpm_id: ID do BPM a atualizar.
            valor: True ativa o isolamento, False desativa.
            admin_id: ID do admin que executou a ação (auditoria).

        Returns:
            BPM atualizado com o novo valor.

        Raises:
            NaoEncontradoError: Se o BPM não existe ou está inativo.
        """
        result = await self.db.execute(
            select(Bpm).where(
                Bpm.id == bpm_id,
                Bpm.ativo == True,  # noqa: E712
            )
        )
        bpm = result.scalar_one_or_none()
        if not bpm:
            raise NaoEncontradoError("BPM não encontrado")

        bpm.isolamento_abordagens = valor
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="bpm",
            recurso_id=bpm.id,
            detalhes={"acao": "toggle_isolamento", "valor": valor},
        )
        return bpm
