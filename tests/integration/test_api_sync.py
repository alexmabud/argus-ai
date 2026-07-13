"""Testes de integração da API de Sincronização.

Testa endpoint POST /sync/batch com itens válidos,
inválidos e deduplicação por client_id.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo


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

    async def test_sync_batch_usuario_sem_guarnicao_auto_atribui(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Usuário sem guarnicao_id não deve quebrar o sync (achado #18/2026-07-13).

        Antes, os handlers internos (_sync_pessoa/_sync_veiculo/_sync_abordagem)
        confiavam em `assert user.guarnicao_id is not None`: um usuário sem
        guarnição batia nesse assert em vez de receber a guarnição padrão
        auto-atribuída, como já acontece nos demais endpoints de criação. O
        router de sync agora usa get_current_user_with_guarnicao, que garante
        a atribuição antes de chegar ao service.

        Args:
            client: Cliente HTTP assíncrono.
            db_session: Sessão do banco de testes.
        """
        usuario_sem_guarnicao = Usuario(
            nome="Agente Sem Equipe",
            matricula="TEST-SEM-GUARN",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=None,
            session_id="test-session-sem-guarn",
        )
        db_session.add(usuario_sem_guarnicao)
        await db_session.flush()

        token = criar_access_token(
            {"sub": str(usuario_sem_guarnicao.id), "sid": usuario_sem_guarnicao.session_id}
        )
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/sync/batch",
            json={
                "items": [
                    {
                        "client_id": "sync-sem-guarn-1",
                        "tipo": "pessoa",
                        "dados": {"nome": "PESSOA SEM GUARNICAO"},
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["status"] == "ok"

        row = (
            await db_session.execute(select(Pessoa).where(Pessoa.nome == "PESSOA SEM GUARNICAO"))
        ).scalar_one_or_none()
        assert row is not None
        assert row.guarnicao_id is not None

    async def test_sync_batch_persiste_veiculo(
        self, client: AsyncClient, auth_headers: dict, usuario, db_session: AsyncSession
    ):
        """Happy path: um item válido de veículo é criado de fato no banco.

        Espelha test_sync_batch_persiste_pessoa (achado #18/2026-07-13):
        veículo também precisa de client_id propagado para deduplicação.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            usuario: Fixture de usuário autenticado (com guarnição).
            db_session: Sessão do banco de testes.
        """
        resp = await client.post(
            "/api/v1/sync/batch",
            json={
                "items": [
                    {
                        "client_id": "sync-veiculo-happy-1",
                        "tipo": "veiculo",
                        "dados": {"placa": "SYN1C23", "modelo": "Gol"},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["status"] == "ok"

        row = (
            await db_session.execute(select(Veiculo).where(Veiculo.placa == "SYN1C23"))
        ).scalar_one_or_none()
        assert row is not None
        assert row.guarnicao_id == usuario.guarnicao_id
        assert row.client_id == "sync-veiculo-happy-1"

    async def test_sync_batch_pessoa_client_id_retry_nao_duplica(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Reenviar o mesmo item de pessoa (retry de rede) não cria duplicata.

        Simula o cenário real de sync offline: o dispositivo reenvia o batch
        porque não recebeu a resposta anterior (timeout), mas o client_id já
        foi persistido — o segundo envio deve ser idempotente (achado #18/
        2026-07-13, antes pessoas sem CPF não tinham nenhuma proteção contra
        duplicação em retry).

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão do banco de testes.
        """
        payload = {
            "items": [
                {
                    "client_id": "sync-pessoa-retry-1",
                    "tipo": "pessoa",
                    "dados": {"nome": "PESSOA RETRY SYNC"},
                }
            ]
        }
        primeira = await client.post("/api/v1/sync/batch", json=payload, headers=auth_headers)
        segunda = await client.post("/api/v1/sync/batch", json=payload, headers=auth_headers)
        assert primeira.status_code == 200
        assert segunda.status_code == 200
        assert primeira.json()["results"][0]["status"] == "ok"
        assert segunda.json()["results"][0]["status"] == "ok"

        rows = (
            await db_session.execute(select(Pessoa).where(Pessoa.nome == "PESSOA RETRY SYNC"))
        ).scalars().all()
        assert len(rows) == 1
