"""Serviço de gestão de BPMs (Batalhões de Polícia Militar).

Implementa listagem e criação de BPMs. Sem dependências FastAPI.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError
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
