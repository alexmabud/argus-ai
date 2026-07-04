"""Testes de integração da API de Veículos.

Testa endpoints de listagem, criação, atualização e autocomplete de
veículos, incluindo isolamento multi-tenant.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo


class TestListarVeiculos:
    """Testes do endpoint GET /api/v1/veiculos/."""

    async def test_listar_veiculos_retorna_200(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa listagem de veículos retorna 200 com dados.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo.
        """
        response = await client.get("/api/v1/veiculos/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_buscar_veiculo_por_placa(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa busca por placa retorna veículo correto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com placa ABC1D23.
        """
        response = await client.get(
            "/api/v1/veiculos/", params={"placa": "ABC1"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "ABC1D23" in data[0]["placa"]

    async def test_listar_veiculos_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/veiculos/")
        assert response.status_code == 401


class TestCriarVeiculo:
    """Testes do endpoint POST /api/v1/veiculos/."""

    async def test_criar_veiculo_retorna_201(self, client: AsyncClient, auth_headers: dict):
        """Testa criação de veículo retorna 201.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={
                "placa": "XYZ9A87",
                "modelo": "Civic",
                "cor": "Preto",
                "ano": 2022,
                "tipo": "Carro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["placa"] == "XYZ9A87"

    async def test_criar_veiculo_placa_duplicada_retorna_409(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que placa duplicada retorna 409.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com placa ABC1D23.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={
                "placa": "ABC1D23",
                "modelo": "Palio",
                "cor": "Vermelho",
                "ano": 2018,
                "tipo": "Carro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_criar_veiculo_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que criação sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/veiculos/",
            json={"placa": "AAA1A11", "modelo": "Uno", "cor": "Azul"},
        )
        assert response.status_code == 401


class TestAtualizarVeiculo:
    """Testes do endpoint PUT /api/v1/veiculos/{id}."""

    async def test_atualizar_retorna_200(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa que atualizar veículo retorna 200 com dados atualizados.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com placa ABC1D23.
        """
        response = await client.put(
            f"/api/v1/veiculos/{veiculo.id}",
            json={"modelo": "Onix", "cor": "Preto"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["modelo"] == "ONIX"
        assert data["cor"] == "PRETO"
        assert data["placa"] == veiculo.placa

    async def test_atualizar_campo_omitido_permanece_inalterado(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Campo não enviado no corpo do PUT não é alterado (partial update).

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com ano=2020, tipo="Carro".
        """
        response = await client.put(
            f"/api/v1/veiculos/{veiculo.id}",
            json={"modelo": "Onix"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["modelo"] == "ONIX"
        assert data["ano"] == veiculo.ano
        assert data["tipo"] == veiculo.tipo

    async def test_atualizar_com_null_explicito_limpa_campo(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Enviar null explicitamente para um campo o limpa (diferente de omitir).

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo com cor="Branco".
        """
        response = await client.put(
            f"/api/v1/veiculos/{veiculo.id}",
            json={"cor": None},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cor"] is None
        assert data["modelo"] == veiculo.modelo  # não enviado, permanece

    async def test_atualizar_inexistente_retorna_404(self, client: AsyncClient, auth_headers: dict):
        """Testa que atualizar veículo inexistente retorna 404.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.put(
            "/api/v1/veiculos/99999", json={"cor": "Azul"}, headers=auth_headers
        )
        assert response.status_code == 404

    async def test_atualizar_sem_auth_retorna_401(self, client: AsyncClient, veiculo: Veiculo):
        """Testa que atualizar sem token retorna 401.

        Args:
            client: Cliente HTTP assíncrono.
            veiculo: Fixture de veículo da guarnição.
        """
        response = await client.put(f"/api/v1/veiculos/{veiculo.id}", json={"cor": "Azul"})
        assert response.status_code == 401


class TestAtualizarVeiculoCrossTenant:
    """Testes de isolamento cross-tenant para atualização de veículo."""

    async def test_nao_pode_atualizar_veiculo_de_outro_tenant(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que operador não pode atualizar veículo de outra guarnição.

        Um operador autenticado na guarnição A não deve conseguir atualizar
        um veículo pertencente à guarnição B.

        Args:
            client: Cliente HTTP assíncrono.
            db_session: Sessão do banco de teste.
            guarnicao: Guarnição principal (tenant A).
            usuario: Usuário autenticado da guarnição principal (tenant A).
        """
        bpm_b = Bpm(nome="6o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(
            nome="6a Cia - GU 01",
            bpm_id=bpm_b.id,
            codigo="6BPM-6CIA-GU01-VEIC",
        )
        db_session.add(guarnicao_b)
        await db_session.flush()

        veiculo_b = Veiculo(placa="ZZZ9Z99", guarnicao_id=guarnicao_b.id)
        db_session.add(veiculo_b)
        await db_session.flush()

        token_a = criar_access_token(
            {"sub": str(usuario.id), "guarnicao_id": guarnicao.id, "sid": usuario.session_id}
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        response = await client.put(
            f"/api/v1/veiculos/{veiculo_b.id}", json={"cor": "Vermelho"}, headers=headers_a
        )
        assert response.status_code == 403


class TestLocalidadesVeiculos:
    """Testes do endpoint GET /api/v1/veiculos/localidades."""

    async def test_listar_localidades_retorna_200(
        self, client: AsyncClient, auth_headers: dict, veiculo: Veiculo
    ):
        """Testa autocomplete de modelos e cores retorna 200.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Fixture de veículo para popular dados.
        """
        response = await client.get("/api/v1/veiculos/localidades", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "modelos" in data
        assert "cores" in data
