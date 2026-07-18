"""Testes de integração da API de Abordagens.

Testa endpoint de criação de abordagem em campo.
"""

from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.pessoa import Pessoa


class TestCriarAbordagem:
    """Testes do endpoint POST /api/v1/abordagens/."""

    async def test_criar_abordagem_basica(self, client: AsyncClient, auth_headers: dict):
        """Testa criação de abordagem simples retorna 201.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "latitude": -22.9068,
                "longitude": -43.1729,
                "endereco_texto": "Av. Brasil, 1000 - Centro, RJ",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["endereco_texto"] == "AV. BRASIL, 1000 - CENTRO, RJ"
        assert "id" in data

    async def test_criar_abordagem_com_pessoa(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa criação de abordagem com pessoa vinculada.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua com Pessoa",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    async def test_criar_abordagem_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Sem Auth",
            },
        )
        assert response.status_code == 401


class TestAtualizarAbordagem:
    """Testes do endpoint PATCH /api/v1/abordagens/{id}."""

    async def test_atualizar_observacao_sucesso(self, client: AsyncClient, auth_headers: dict):
        """Testa que observação pode ser adicionada após a criação.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua Sem Observação, 50",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.patch(
            f"/api/v1/abordagens/{abordagem_id}",
            json={"observacao": "Nada consta, apenas orientação verbal."},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["observacao"] == "NADA CONSTA, APENAS ORIENTAÇÃO VERBAL."

    async def test_atualizar_abordagem_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que atualizar abordagem inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.patch(
            "/api/v1/abordagens/999999",
            json={"observacao": "Qualquer coisa"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_atualizar_abordagem_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.patch(
            "/api/v1/abordagens/1",
            json={"observacao": "Qualquer coisa"},
        )
        assert response.status_code == 401

    async def test_atualizar_abordagem_por_outro_usuario_retorna_403(
        self, client: AsyncClient, auth_headers: dict, auth_headers_outro_usuario: dict
    ):
        """Testa que usuário que não é dono nem admin não pode editar a abordagem.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            auth_headers_outro_usuario: Headers de um segundo usuário da mesma
                guarnição, sem privilégio de admin.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 10",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.patch(
            f"/api/v1/abordagens/{abordagem_id}",
            json={"observacao": "Tentativa de edição por terceiro"},
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_atualizar_abordagem_por_admin_sucesso(
        self, client: AsyncClient, auth_headers: dict, auth_headers_admin: dict
    ):
        """Testa que admin da guarnição pode editar abordagem de outro oficial.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem (não-admin).
            auth_headers_admin: Headers de um admin da mesma guarnição.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 20",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.patch(
            f"/api/v1/abordagens/{abordagem_id}",
            json={"observacao": "Edição feita pelo admin"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["observacao"] == "EDIÇÃO FEITA PELO ADMIN"
