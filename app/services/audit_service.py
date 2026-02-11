"""Serviço de auditoria para registrar ações de usuários.

Responsável por criar entradas de log de auditoria para rastrear todas as
ações importantes realizadas no sistema, garantindo conformidade com LGPD
e requisitos de segurança.
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """Serviço para registrar logs de auditoria.

    Cria entradas de auditoria para ações de usuários, incluindo informações
    de contexto como IP, User-Agent e detalhes específicos da ação.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        usuario_id: int,
        acao: str,
        recurso: str,
        recurso_id: int | None = None,
        detalhes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Registra uma ação de auditoria.

        Cria uma entrada de log de auditoria com informações da ação realizada,
        contexto de rede e detalhes adicionais em formato JSON.

        Args:
            usuario_id: Identificador do usuário que realizou a ação.
            acao: Tipo de ação realizada (ex: "CREATE", "UPDATE", "DELETE", "LOGIN").
            recurso: Tipo de recurso afetado (ex: "usuario", "abordagem", "ocorrencia").
            recurso_id: Identificador do recurso específico afetado (opcional).
            detalhes: Dicionário com detalhes adicionais da ação (opcional).
                Será convertido para JSON antes de armazenar.
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            None. A entrada é adicionada à sessão e sincronizada via flush.

        Note:
            A entrada é adicionada com flush mas não commit, permitindo que
            chamadores controlem a transação completa.
        """
        entry = AuditLog(
            usuario_id=usuario_id,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            detalhes=json.dumps(detalhes, ensure_ascii=False) if detalhes else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
