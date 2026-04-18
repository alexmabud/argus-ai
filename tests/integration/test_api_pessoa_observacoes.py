"""Testes de integração para endpoints de observações de pessoas.

Cobre criação, listagem, atualização e soft delete de observações,
incluindo validação de autenticação, dados inválidos e recursos inexistentes.
"""

from httpx import AsyncClient

from app.models.pessoa import Pessoa


class TestCriarObservacao:
    """Testes do endpoint POST /api/v1/pessoas/{pessoa_id}/observacoes."""

    async def test_criar_observacao_retorna_201(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa criação de observação retorna 201 com campos esperados.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Indivíduo usa boné vermelho como sinal de reconhecimento."},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["texto"] == "Indivíduo usa boné vermelho como sinal de reconhecimento."
        assert "id" in data
        assert "criado_em" in data

    async def test_criar_sem_auth_retorna_401(
        self,
        client: AsyncClient,
        pessoa: Pessoa,
    ) -> None:
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Observação sem autenticação."},
        )
        assert response.status_code == 401

    async def test_texto_vazio_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que texto vazio retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_pessoa_inexistente_retorna_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Testa que pessoa inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/pessoas/99999/observacoes",
            json={"texto": "Observação para pessoa inexistente."},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListarObservacoes:
    """Testes do endpoint GET /api/v1/pessoas/{pessoa_id}/observacoes."""

    async def test_listar_retorna_lista_vazia(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que listagem retorna lista vazia quando não há observações.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_listar_retorna_observacoes_criadas(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que listagem retorna observações criadas, da mais recente para a mais antiga.

        Cria duas observações e verifica que ambas são retornadas em ordem
        decrescente de criação (mais recente primeiro).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Primeira observação criada."},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Segunda observação criada."},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Mais recente primeiro
        assert data[0]["texto"] == "Segunda observação criada."
        assert data[1]["texto"] == "Primeira observação criada."


class TestAtualizarObservacao:
    """Testes do endpoint PATCH /api/v1/pessoas/{pessoa_id}/observacoes/{obs_id}."""

    async def test_atualizar_texto_retorna_200(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que atualização do texto retorna 200 com novo conteúdo.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Texto original da observação."},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            json={"texto": "Texto atualizado da observação."},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == obs_id
        assert data["texto"] == "Texto atualizado da observação."

    async def test_obs_inexistente_retorna_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que atualização de observação inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.patch(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/99999",
            json={"texto": "Texto para observação inexistente."},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeletarObservacao:
    """Testes do endpoint DELETE /api/v1/pessoas/{pessoa_id}/observacoes/{obs_id}."""

    async def test_deletar_retorna_204(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que deleção de observação retorna 204.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Observação a ser deletada."},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_obs_deletada_nao_aparece_na_listagem(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa: Pessoa,
    ) -> None:
        """Testa que observação deletada não aparece na listagem (soft delete).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Observação que será removida da listagem."},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            headers=auth_headers,
        )

        list_resp = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        ids_listados = [o["id"] for o in list_resp.json()]
        assert obs_id not in ids_listados
