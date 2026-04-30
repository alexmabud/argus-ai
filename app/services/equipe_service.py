"""Serviço de gestão de equipes (guarnições) pelo administrador.

Implementa criação de novas equipes com código gerado automaticamente,
listagem e alternância do toggle de isolamento de abordagens.
Sem dependências FastAPI.

NOTA: "Equipe" na UI = "Guarnicao" no código/banco.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.services.audit_service import AuditService


def _gerar_codigo(nome: str, unidade: str) -> str:
    """Gera código alfanumérico a partir de nome e unidade.

    Remove caracteres não alfanuméricos, normaliza para upper-case e trunca
    em 50 chars. Ex: ("3ª Cia - GU 01", "3º BPM") -> "3BPM-3CIAGU01".

    Args:
        nome: Nome da equipe.
        unidade: Unidade superior.

    Returns:
        Código alfanumérico em upper-case (máx 50 chars).
    """

    def _slug(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", s).upper()

    base = f"{_slug(unidade)}-{_slug(nome)}"
    return base[:50] or "EQUIPE"


class EquipeService:
    """Serviço de gestão de equipes (guarnições) para uso do administrador.

    Cobre criação com código automático, listagem e toggle de isolamento
    de abordagens por equipe. Registra todas as mutações via AuditService.

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

    async def listar_equipes(self) -> list[Guarnicao]:
        """Lista todas as equipes ativas, ordenadas por nome.

        Returns:
            Lista de Guarnicao com ativo=True.
        """
        result = await self.db.execute(
            select(Guarnicao)
            .where(Guarnicao.ativo == True)  # noqa: E712
            .order_by(Guarnicao.nome)
        )
        return list(result.scalars().all())

    async def criar_equipe(self, nome: str, unidade: str, admin_id: int) -> Guarnicao:
        """Cria nova equipe com código gerado automaticamente.

        Se o código gerado colidir com um existente, adiciona sufixo numérico
        (-2, -3, …) até encontrar um código único.

        Args:
            nome: Nome descritivo da equipe.
            unidade: Unidade superior (ex: "3º BPM").
            admin_id: ID do admin que está criando (auditoria).

        Returns:
            Equipe criada com ID atribuído.

        Raises:
            ConflitoDadosError: Se já existe equipe ativa com o mesmo nome.
        """
        existing = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.nome == nome,
                Guarnicao.ativo == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise ConflitoDadosError("Já existe uma equipe ativa com este nome")

        codigo_base = _gerar_codigo(nome, unidade)
        codigo = codigo_base
        i = 2
        while True:
            exists = await self.db.execute(select(Guarnicao.id).where(Guarnicao.codigo == codigo))
            if exists.scalar_one_or_none() is None:
                break
            codigo = f"{codigo_base[:48]}-{i}"
            i += 1

        equipe = Guarnicao(nome=nome, unidade=unidade, codigo=codigo)
        self.db.add(equipe)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="guarnicao",
            recurso_id=equipe.id,
            detalhes={"nome": nome, "unidade": unidade},
        )
        return equipe

    async def toggle_isolamento(self, guarnicao_id: int, valor: bool, admin_id: int) -> Guarnicao:
        """Define o valor de isolamento_abordagens da equipe.

        Args:
            guarnicao_id: ID da equipe.
            valor: True ativa o isolamento, False desativa.
            admin_id: ID do admin (auditoria).

        Returns:
            Equipe atualizada com o novo valor.

        Raises:
            NaoEncontradoError: Se a equipe não existe ou está inativa.
        """
        result = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.id == guarnicao_id,
                Guarnicao.ativo == True,  # noqa: E712
            )
        )
        equipe = result.scalar_one_or_none()
        if not equipe:
            raise NaoEncontradoError("Equipe não encontrada")

        equipe.isolamento_abordagens = valor
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="guarnicao",
            recurso_id=equipe.id,
            detalhes={"acao": "toggle_isolamento", "valor": valor},
        )
        return equipe
