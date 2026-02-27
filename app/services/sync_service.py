"""Serviço de sincronização offline → online.

Processa batch de itens criados offline pelo frontend PWA,
com deduplicação por client_id para garantir idempotência.
Suporta criação de abordagens, pessoas e veículos.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.models.usuario import Usuario
from app.schemas.sync import SyncItem, SyncItemResult
from app.services.abordagem_service import AbordagemService
from app.services.pessoa_service import PessoaService
from app.services.veiculo_service import VeiculoService

logger = logging.getLogger("argus")


class SyncService:
    """Serviço de sincronização batch offline → online.

    Processa lista de itens criados offline, verificando
    deduplicação por client_id antes de criar registros.
    Cada item é processado independentemente para evitar
    que uma falha afete os demais.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de sincronização.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db

    async def process_batch(self, items: list[SyncItem], user: Usuario) -> list[SyncItemResult]:
        """Processa batch de itens offline.

        Cada item é processado individualmente. Se um item falhar,
        os demais continuam sendo processados. Deduplicação por
        client_id garante idempotência.

        Args:
            items: Lista de itens a sincronizar.
            user: Usuário autenticado que criou os itens.

        Returns:
            Lista de resultados com status por item.
        """
        results = []
        for item in items:
            try:
                result = await self._process_item(item, user)
                results.append(result)
            except Exception as e:
                logger.error("Erro sync item %s: %s", item.client_id, str(e))
                results.append(
                    SyncItemResult(
                        client_id=item.client_id,
                        status="error",
                        error=str(e),
                    )
                )
        return results

    async def _process_item(self, item: SyncItem, user: Usuario) -> SyncItemResult:
        """Processa um item individual de sync.

        Args:
            item: Item a processar.
            user: Usuário autenticado.

        Returns:
            Resultado do processamento.
        """
        # Deduplicação por client_id para abordagens
        if item.tipo == "abordagem" and item.client_id:
            existing = await self.db.execute(
                select(Abordagem.id).where(Abordagem.client_id == item.client_id)
            )
            if existing.scalar_one_or_none():
                return SyncItemResult(client_id=item.client_id, status="ok")

        handlers = {
            "abordagem": self._sync_abordagem,
            "pessoa": self._sync_pessoa,
            "veiculo": self._sync_veiculo,
        }

        handler = handlers.get(item.tipo)
        if not handler:
            return SyncItemResult(
                client_id=item.client_id,
                status="error",
                error=f"Tipo desconhecido: {item.tipo}",
            )

        await handler(item.dados, user)
        await self.db.commit()

        return SyncItemResult(client_id=item.client_id, status="ok")

    async def _sync_abordagem(self, dados: dict, user: Usuario) -> None:
        """Sincroniza abordagem offline.

        Args:
            dados: Payload da abordagem.
            user: Usuário autenticado.
        """
        from app.schemas.abordagem import AbordagemCreate

        service = AbordagemService(self.db)
        data = AbordagemCreate(
            data_hora=dados.get("data_hora"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
            endereco_texto=dados.get("endereco_texto"),
            observacao=dados.get("observacao"),
            origem=dados.get("origem", "offline"),
            client_id=dados.get("client_id"),
            pessoa_ids=dados.get("pessoa_ids", []),
            veiculo_ids=dados.get("veiculo_ids", []),
            passagens=[],
        )
        await service.criar(
            data=data,
            user_id=user.id,
            guarnicao_id=user.guarnicao_id,
        )

    async def _sync_pessoa(self, dados: dict, user: Usuario) -> None:
        """Sincroniza pessoa offline.

        Args:
            dados: Payload da pessoa.
            user: Usuário autenticado.
        """
        from app.schemas.pessoa import PessoaCreate

        service = PessoaService(self.db)
        data = PessoaCreate(
            nome=dados["nome"],
            cpf=dados.get("cpf"),
            data_nascimento=dados.get("data_nascimento"),
            apelido=dados.get("apelido"),
            observacoes=dados.get("observacoes"),
        )
        await service.criar(
            data=data,
            user_id=user.id,
            guarnicao_id=user.guarnicao_id,
        )

    async def _sync_veiculo(self, dados: dict, user: Usuario) -> None:
        """Sincroniza veículo offline.

        Args:
            dados: Payload do veículo.
            user: Usuário autenticado.
        """
        from app.schemas.veiculo import VeiculoCreate

        service = VeiculoService(self.db)
        data = VeiculoCreate(
            placa=dados["placa"],
            modelo=dados.get("modelo"),
            cor=dados.get("cor"),
            ano=dados.get("ano"),
            tipo=dados.get("tipo"),
            observacoes=dados.get("observacoes"),
        )
        await service.criar(
            data=data,
            user_id=user.id,
            guarnicao_id=user.guarnicao_id,
        )
