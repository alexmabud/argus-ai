"""Testes de integração para endpoints de legislação.

Valida listagem, busca por ID e busca semântica via API.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legislacao import Legislacao


@pytest.fixture
async def legislacao(db_session: AsyncSession) -> Legislacao:
    """Fixture que cria um artigo de legislação de teste.

    Args:
        db_session: Sessão do banco de testes.

    Returns:
        Legislacao: Art. 157 CP (Roubo).
    """
    leg = Legislacao(
        lei="CP",
        artigo="157",
        nome="Roubo",
        texto=(
            "Subtrair coisa móvel alheia, para si ou para outrem, "
            "mediante grave ameaça ou violência."
        ),
    )
    db_session.add(leg)
    await db_session.flush()
    return leg


class TestListarLegislacao:
    """Testes para GET /legislacao."""

    @pytest.mark.asyncio
    async def test_retorna_200(
        self, client: AsyncClient, auth_headers: dict, legislacao: Legislacao
    ):
        """Deve retornar 200 com lista de legislações."""
        response = await client.get("/api/v1/legislacao/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["lei"] == "CP"

    @pytest.mark.asyncio
    async def test_sem_auth_retorna_401(self, client: AsyncClient, legislacao: Legislacao):
        """Deve retornar 401 sem autenticação."""
        response = await client.get("/api/v1/legislacao/")
        assert response.status_code in (401, 403)


class TestDetalheLegislacao:
    """Testes para GET /legislacao/{id}."""

    @pytest.mark.asyncio
    async def test_retorna_200(
        self, client: AsyncClient, auth_headers: dict, legislacao: Legislacao
    ):
        """Deve retornar legislação por ID."""
        response = await client.get(f"/api/v1/legislacao/{legislacao.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["artigo"] == "157"

    @pytest.mark.asyncio
    async def test_id_inexistente_retorna_404(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 404 para ID inexistente."""
        response = await client.get("/api/v1/legislacao/99999", headers=auth_headers)
        assert response.status_code == 404
