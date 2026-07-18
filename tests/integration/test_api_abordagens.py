"""Testes de integração da API de Abordagens.

Testa endpoint de criação de abordagem em campo.
"""

from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.pessoa import Pessoa
from app.models.veiculo import Veiculo


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


class TestVincularPessoa:
    """Testes do endpoint POST /api/v1/abordagens/{id}/pessoas."""

    async def test_dono_vincula_pessoa_existente_sucesso(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que o dono da abordagem consegue vincular pessoa já cadastrada.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua Sem Pessoa, 10",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas",
            json={"pessoa_id": pessoa.id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        pessoa_ids = [p["id"] for p in response.json()["pessoas"]]
        assert pessoa.id in pessoa_ids

    async def test_terceiro_nao_pode_vincular_pessoa_retorna_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_outro_usuario: dict,
        pessoa: Pessoa,
    ):
        """Testa que usuário que não é dono nem admin não pode vincular pessoa.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            auth_headers_outro_usuario: Headers de terceiro sem privilégio de admin.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 30",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas",
            json={"pessoa_id": pessoa.id},
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_admin_vincula_pessoa_em_abordagem_de_outro(
        self, client: AsyncClient, auth_headers: dict, auth_headers_admin: dict, pessoa: Pessoa
    ):
        """Testa que admin da guarnição pode vincular pessoa em abordagem de outro oficial.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem (não-admin).
            auth_headers_admin: Headers de um admin da mesma guarnição.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 40",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas",
            json={"pessoa_id": pessoa.id},
            headers=auth_headers_admin,
        )
        assert response.status_code == 201
        pessoa_ids = [p["id"] for p in response.json()["pessoas"]]
        assert pessoa.id in pessoa_ids

    async def test_vincular_pessoa_ja_vinculada_retorna_409(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que vincular a mesma pessoa duas vezes retorna 409, não 500.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 50",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas",
            json={"pessoa_id": pessoa.id},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestDesvincularPessoa:
    """Testes do endpoint DELETE /api/v1/abordagens/{id}/pessoas/{pessoa_id}."""

    async def test_dono_desvincula_pessoa_sucesso(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que o dono da abordagem consegue desvincular uma pessoa.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 60",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        detalhe = await client.get(f"/api/v1/abordagens/{abordagem_id}", headers=auth_headers)
        pessoa_ids = [p["id"] for p in detalhe.json()["pessoas"]]
        assert pessoa.id not in pessoa_ids

    async def test_terceiro_nao_pode_desvincular_retorna_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_outro_usuario: dict,
        pessoa: Pessoa,
    ):
        """Testa que usuário que não é dono nem admin não pode desvincular pessoa.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            auth_headers_outro_usuario: Headers de terceiro sem privilégio de admin.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 70",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_desvincular_pessoa_nao_vinculada_retorna_404(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que desvincular pessoa não vinculada retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            pessoa: Fixture de pessoa já cadastrada (mas não vinculada).
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 80",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_vincular_apos_desvincular_reativa_vinculo(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que vincular novamente após desvincular reativa o vínculo antigo.

        Reproduz o cenário de soft-delete: desvincula, depois vincula de novo.
        Deve reativar o vínculo em vez de tentar inserir uma linha duplicada.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            pessoa: Fixture de pessoa já cadastrada.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 90",
                "pessoa_ids": [pessoa.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        desvinculo = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/pessoas/{pessoa.id}",
            headers=auth_headers,
        )
        assert desvinculo.status_code == 204

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/pessoas",
            json={"pessoa_id": pessoa.id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        pessoa_ids = [p["id"] for p in response.json()["pessoas"]]
        assert pessoa.id in pessoa_ids


class TestVincularVeiculo:
    """Testes do endpoint POST /api/v1/abordagens/{id}/veiculos."""

    async def test_dono_vincula_veiculo_existente_sucesso(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que o dono da abordagem consegue vincular veículo já cadastrado.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua Sem Veículo, 10",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/veiculos",
            json={"veiculo_id": veiculo.id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        veiculo_ids = [v["id"] for v in response.json()["veiculos"]]
        assert veiculo.id in veiculo_ids

    async def test_terceiro_nao_pode_vincular_veiculo_retorna_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_outro_usuario: dict,
        veiculo: Veiculo,
    ):
        """Testa que usuário que não é dono nem admin não pode vincular veículo.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            auth_headers_outro_usuario: Headers de terceiro sem privilégio de admin.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 30",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/veiculos",
            json={"veiculo_id": veiculo.id},
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_admin_vincula_veiculo_em_abordagem_de_outro(
        self, client: AsyncClient, auth_headers: dict, auth_headers_admin: dict, veiculo: Veiculo
    ):
        """Testa que admin da guarnição pode vincular veículo em abordagem de outro oficial.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem (não-admin).
            auth_headers_admin: Headers de um admin da mesma guarnição.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 40",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/veiculos",
            json={"veiculo_id": veiculo.id},
            headers=auth_headers_admin,
        )
        assert response.status_code == 201
        veiculo_ids = [v["id"] for v in response.json()["veiculos"]]
        assert veiculo.id in veiculo_ids

    async def test_vincular_veiculo_ja_vinculado_retorna_409(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que vincular o mesmo veículo duas vezes retorna 409, não 500.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 50",
                "veiculo_ids": [veiculo.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/veiculos",
            json={"veiculo_id": veiculo.id},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestDesvincularVeiculo:
    """Testes do endpoint DELETE /api/v1/abordagens/{id}/veiculos/{veiculo_id}."""

    async def test_dono_desvincula_veiculo_sucesso(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que o dono da abordagem consegue desvincular um veículo.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 60",
                "veiculo_ids": [veiculo.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/veiculos/{veiculo.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        detalhe = await client.get(f"/api/v1/abordagens/{abordagem_id}", headers=auth_headers)
        veiculo_ids = [v["id"] for v in detalhe.json()["veiculos"]]
        assert veiculo.id not in veiculo_ids

    async def test_terceiro_nao_pode_desvincular_veiculo_retorna_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_outro_usuario: dict,
        veiculo: Veiculo,
    ):
        """Testa que usuário que não é dono nem admin não pode desvincular veículo.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            auth_headers_outro_usuario: Headers de terceiro sem privilégio de admin.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 70",
                "veiculo_ids": [veiculo.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/veiculos/{veiculo.id}",
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_desvincular_veiculo_nao_vinculado_retorna_404(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que desvincular veículo não vinculado retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            veiculo: Fixture de veículo já cadastrado (mas não vinculado).
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 80",
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        response = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/veiculos/{veiculo.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_vincular_apos_desvincular_reativa_vinculo_veiculo(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que vincular novamente após desvincular reativa o vínculo antigo.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers do usuário dono da abordagem.
            veiculo: Fixture de veículo já cadastrado.
        """
        criada = await client.post(
            "/api/v1/abordagens/",
            json={
                "data_hora": datetime.now(UTC).isoformat(),
                "endereco_texto": "Rua do Dono, 90",
                "veiculo_ids": [veiculo.id],
            },
            headers=auth_headers,
        )
        abordagem_id = criada.json()["id"]

        desvinculo = await client.delete(
            f"/api/v1/abordagens/{abordagem_id}/veiculos/{veiculo.id}",
            headers=auth_headers,
        )
        assert desvinculo.status_code == 204

        response = await client.post(
            f"/api/v1/abordagens/{abordagem_id}/veiculos",
            json={"veiculo_id": veiculo.id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        veiculo_ids = [v["id"] for v in response.json()["veiculos"]]
        assert veiculo.id in veiculo_ids
