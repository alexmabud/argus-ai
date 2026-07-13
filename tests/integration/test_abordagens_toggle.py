"""Testes do toggle de isolamento de abordagens por equipe."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


@pytest.fixture
async def equipe_b(db_session: AsyncSession, bpm) -> Guarnicao:
    """Segunda equipe de teste."""
    g = Guarnicao(nome="GU B", bpm_id=bpm.id, codigo="2BPM-GUB")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_b(db_session: AsyncSession, equipe_b: Guarnicao) -> Usuario:
    """Usuário ativo na equipe B."""
    u = Usuario(
        nome="Agente B",
        matricula="BBB001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=equipe_b.id,
        session_id="session-b",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_b(usuario_b: Usuario) -> dict:
    """Headers do usuário B."""
    token = criar_access_token(
        {
            "sub": str(usuario_b.id),
            "guarnicao_id": usuario_b.guarnicao_id,
            "sid": usuario_b.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def abordagem_b(
    db_session: AsyncSession, equipe_b: Guarnicao, usuario_b: Usuario
) -> Abordagem:
    """Abordagem registrada pela equipe B."""
    a = Abordagem(
        guarnicao_id=equipe_b.id,
        usuario_id=usuario_b.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av B 100",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_isolamento_off_usuario_a_ve_abordagem_de_b(
    client: AsyncClient,
    auth_headers,
    abordagem,
    abordagem_b,
    guarnicao,
):
    """Quando isolamento=False, usuário da equipe A vê abordagens de B também."""
    assert guarnicao.isolamento_abordagens is False
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_b.id in ids


@pytest.mark.asyncio
async def test_isolamento_on_usuario_a_nao_ve_abordagem_de_b(
    client: AsyncClient,
    auth_headers,
    db_session,
    guarnicao,
    abordagem,
    abordagem_b,
):
    """Quando isolamento=True, usuário da equipe A vê apenas abordagens de A."""
    guarnicao.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_b.id not in ids


@pytest.mark.asyncio
async def test_detalhe_abordagem_de_outra_equipe_isolamento_off(
    client: AsyncClient, auth_headers, abordagem_b
):
    """Com isolamento OFF, usuário de A consegue abrir detalhe de abordagem de B."""
    response = await client.get(f"/api/v1/abordagens/{abordagem_b.id}", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_detalhe_abordagem_de_outra_equipe_isolamento_on_404(
    client: AsyncClient, auth_headers, db_session, guarnicao, abordagem_b
):
    """Com isolamento ON, detalhe de abordagem de B retorna 404 para usuário de A."""
    guarnicao.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get(f"/api/v1/abordagens/{abordagem_b.id}", headers=auth_headers)
    assert response.status_code == 404


class TestFotosAbordagemAuthz:
    """Testes de autorização de GET /fotos/abordagem/{id} (achado #22/2026-07-13)."""

    async def test_listar_fotos_de_abordagem_de_outra_equipe_isolamento_off(
        self, client: AsyncClient, auth_headers, abordagem_b
    ):
        """Com isolamento OFF, usuário de A lista fotos de abordagem de B (200)."""
        response = await client.get(
            f"/api/v1/fotos/abordagem/{abordagem_b.id}", headers=auth_headers
        )
        assert response.status_code == 200

    async def test_listar_fotos_de_abordagem_de_outra_equipe_isolamento_on_404(
        self, client: AsyncClient, auth_headers, db_session, guarnicao, abordagem_b
    ):
        """Com isolamento ON, listar fotos de abordagem de B retorna 404 para A.

        Antes desta correção, qualquer autenticado listava fotos de
        QUALQUER abordagem só sabendo o ID — o endpoint não checava
        isolamento_abordagens nenhum.
        """
        guarnicao.isolamento_abordagens = True
        await db_session.flush()
        response = await client.get(
            f"/api/v1/fotos/abordagem/{abordagem_b.id}", headers=auth_headers
        )
        assert response.status_code == 404


class TestCriarOcorrenciaAbordagemAuthz:
    """Testes de autorização de abordagem_id em POST /ocorrencias/ (achado #22/2026-07-13)."""

    async def _post_ocorrencia(
        self, client: AsyncClient, headers: dict, abordagem_id: int, numero: str
    ):
        """Faz POST multipart em /ocorrencias/ com storage mockado."""
        mock_storage = AsyncMock()
        mock_storage.upload = AsyncMock(return_value="https://r2.example.com/pdfs/fake.pdf")
        mock_storage.generate_key = lambda prefix, filename: f"{prefix}/fake.pdf"
        with patch("app.services.ocorrencia_service.StorageService") as mock_cls:
            mock_cls.get = lambda: mock_storage
            return await client.post(
                "/api/v1/ocorrencias/",
                data={
                    "numero_ocorrencia": numero,
                    "abordagem_id": str(abordagem_id),
                    "data_ocorrencia": date.today().isoformat(),
                },
                files={"arquivo_pdf": ("bo.pdf", b"%PDF-1.7 fake content", "application/pdf")},
                headers=headers,
            )

    async def test_criar_ocorrencia_com_abordagem_de_outra_equipe_isolamento_off(
        self, client: AsyncClient, auth_headers, abordagem_b
    ):
        """Com isolamento OFF, vincular ocorrência à abordagem de B é aceito (201)."""
        response = await self._post_ocorrencia(
            client, auth_headers, abordagem_b.id, "RAP 2026/AUTHZ-OFF"
        )
        assert response.status_code == 201

    async def test_criar_ocorrencia_com_abordagem_de_outra_equipe_isolamento_on_404(
        self, client: AsyncClient, auth_headers, db_session, guarnicao, abordagem_b
    ):
        """Com isolamento ON, vincular ocorrência à abordagem de B é rejeitado (404).

        Antes desta correção, abordagem_id era gravado sem nenhuma validação
        de existência ou de escopo — um abordagem_id de outra equipe (ou
        inexistente) era aceito silenciosamente.
        """
        guarnicao.isolamento_abordagens = True
        await db_session.flush()
        response = await self._post_ocorrencia(
            client, auth_headers, abordagem_b.id, "RAP 2026/AUTHZ-ON"
        )
        assert response.status_code == 404

    async def test_criar_ocorrencia_com_abordagem_inexistente_404(
        self, client: AsyncClient, auth_headers
    ):
        """abordagem_id inexistente é rejeitado (404), não gravado silenciosamente."""
        response = await self._post_ocorrencia(client, auth_headers, 999999, "RAP 2026/INEXISTENTE")
        assert response.status_code == 404
