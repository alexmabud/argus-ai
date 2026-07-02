"""Testes de integração da API de Sincronização.

Testa endpoint POST /sync/batch com itens válidos,
inválidos e deduplicação por client_id.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pessoa import Pessoa


class TestSyncBatch:
    """Testes do endpoint POST /api/v1/sync/batch."""

    async def test_sync_batch_tipo_invalido(self, client: AsyncClient, auth_headers: dict):
        """Tipo desconhecido deve ser rejeitado em validacao (422).

        Apos Task 18, SyncItem.tipo eh Literal[...] — Pydantic rejeita antes
        de chegar ao service. Antes, o service respondia 200 com status=error.
        Falhar cedo eh melhor: nao consome tempo do worker com lixo.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={
                "items": [
                    {
                        "client_id": "test-uuid-1",
                        "tipo": "tipo_invalido",
                        "dados": {"foo": "bar"},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_sync_batch_vazio(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar batch vazio sem erro.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={"items": []},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["results"] == []

    async def test_sync_batch_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/sync/batch",
            json={"items": []},
        )
        assert response.status_code == 401

    async def test_sync_batch_persiste_pessoa(
        self, client: AsyncClient, auth_headers: dict, usuario, db_session: AsyncSession
    ):
        """Happy path: um item válido de pessoa é criado de fato no banco.

        Antes a suíte só cobria 422 (tipo inválido) e 200 (batch vazio) — a
        persistência real nunca era exercida (achado #2 do Grupo 9).

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            usuario: Fixture de usuário autenticado (com guarnição).
            db_session: Sessão do banco de testes (para verificar persistência).
        """
        resp = await client.post(
            "/api/v1/sync/batch",
            json={
                "items": [
                    {
                        "client_id": "sync-pessoa-happy-1",
                        "tipo": "pessoa",
                        "dados": {"nome": "FULANO SYNC TESTE"},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["status"] == "ok"

        # Persistência real no banco — não só o status na resposta.
        row = (
            await db_session.execute(select(Pessoa).where(Pessoa.nome == "FULANO SYNC TESTE"))
        ).scalar_one_or_none()
        assert row is not None
        assert row.guarnicao_id == usuario.guarnicao_id
