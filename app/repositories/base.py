"""Repositório genérico com operações CRUD, soft delete e multi-tenancy.

Fornece a base para todos os repositórios específicos do domínio, implementando
operações comuns de acesso a dados (create, read, update, delete) e padrões
como soft delete e filtros multi-tenant.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Repositório genérico com CRUD, soft delete e multi-tenancy.

    Implementa operações básicas (create, read, update, delete) para qualquer
    modelo SQLAlchemy. Aplica automaticamente filtros de soft delete (ativo=True)
    e multi-tenancy (guarnicao_id), quando os atributos existem no modelo.

    Type Parameters:
        T: Tipo do modelo SQLAlchemy vinculado a este repositório.

    Attributes:
        model: Classe do modelo SQLAlchemy.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, model: type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> T | None:
        """Obtém um recurso por identificador.

        Args:
            id: Identificador único do recurso.

        Returns:
            Objeto do modelo se encontrado, None caso contrário.
        """
        result = await self.db.execute(select(self.model).where(getattr(self.model, "id") == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        guarnicao_id: int | None = None,
    ) -> Sequence[T]:
        """Obtém todos os recursos com paginação e filtros.

        Aplica automaticamente filtros de soft delete (ativo=True) e multi-tenancy
        (guarnicao_id) quando os atributos existem no modelo.

        Args:
            skip: Número de registros a pular (padrão: 0).
            limit: Número máximo de registros a retornar (padrão: 100).
            guarnicao_id: Identificador da guarnição para filtro multi-tenant.
                Se None, retorna recursos de todas as guarnições (padrão).

        Returns:
            Sequência de objetos do modelo encontrados.
        """
        query = select(self.model)

        if hasattr(self.model, "ativo"):
            query = query.where(getattr(self.model, "ativo") == True)  # noqa: E712

        if guarnicao_id is not None and hasattr(self.model, "guarnicao_id"):
            query = query.where(getattr(self.model, "guarnicao_id") == guarnicao_id)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        """Cria um novo recurso.

        Adiciona o objeto à sessão e executa flush para sincronizar com o banco
        (sem fazer commit completo).

        Args:
            obj: Instância do modelo a ser criada.

        Returns:
            Objeto criado com ID atribuído pelo banco.
        """
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, obj: T, data: dict) -> T:
        """Atualiza um recurso existente.

        Modifica os atributos do objeto com os valores fornecidos no dicionário
        e executa flush para sincronizar com o banco.

        Args:
            obj: Instância do modelo a ser atualizada.
            data: Dicionário com pares chave-valor dos atributos a atualizar.

        Returns:
            Objeto atualizado.
        """
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def soft_delete(self, obj: T, deleted_by_id: int | None = None) -> T:
        """Desativa um recurso (soft delete).

        Marca o recurso como inativo sem removê-lo fisicamente do banco de dados.
        Registra a data e hora da desativação e, opcionalmente, o usuário que
        realizou a ação.

        Args:
            obj: Instância do modelo a ser desativada.
            deleted_by_id: Identificador do usuário que realizou a desativação.
                Se None, apenas marca como inativo (padrão).

        Returns:
            Objeto desativado.

        Note:
            Este método só funciona se o modelo possui os atributos:
            - ativo (bool)
            - desativado_em (datetime)
            - desativado_por_id (int, opcional)
        """
        if hasattr(obj, "ativo"):
            setattr(obj, "ativo", False)
            if hasattr(obj, "desativado_em"):
                setattr(obj, "desativado_em", datetime.now(UTC))
            if hasattr(obj, "desativado_por_id") and deleted_by_id is not None:
                setattr(obj, "desativado_por_id", deleted_by_id)
            await self.db.flush()
        return obj
