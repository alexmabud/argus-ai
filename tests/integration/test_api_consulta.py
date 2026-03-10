"""Testes de integração da API de Consulta Unificada.

Testa endpoint de busca cross-domain em pessoas, veículos
e abordagens através de um único termo de busca.
Também testa o endpoint de busca de pessoas por veículo.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao


class TestConsultaUnificada:
    """Testes do endpoint GET /api/v1/consultas/."""

    async def test_consulta_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Testa que consulta válida retorna 200 com estrutura correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=teste",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "pessoas" in data
        assert "veiculos" in data
        assert "abordagens" in data
        assert "total_resultados" in data

    async def test_consulta_sem_termo_retorna_422(self, client: AsyncClient, auth_headers: dict):
        """Testa que consulta sem termo de busca retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_consulta_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que consulta sem autenticação retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/consultas/?q=teste")
        assert response.status_code == 401

    async def test_consulta_filtro_tipo_pessoa(self, client: AsyncClient, auth_headers: dict):
        """Testa consulta filtrando por tipo 'pessoa'.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=joao&tipo=pessoa",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Quando filtrando por pessoa, veículos e abordagens devem estar vazios
        assert data["veiculos"] == []
        assert data["abordagens"] == []

    async def test_consulta_paginacao(self, client: AsyncClient, auth_headers: dict):
        """Testa que parâmetros de paginação são aceitos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=teste&skip=0&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_consulta_por_bairro_retorna_endereco_criado_em(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
    ):
        """Testa que busca por bairro retorna endereco_criado_em nos resultados.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão do banco de dados de teste.
            guarnicao: Guarnição de teste.
        """
        from app.models.endereco import EnderecoPessoa
        from app.models.pessoa import Pessoa

        # Criar pessoa com endereço
        pessoa = Pessoa(nome="Teste Bairro", guarnicao_id=guarnicao.id)
        db_session.add(pessoa)
        await db_session.flush()

        endereco = EnderecoPessoa(
            pessoa_id=pessoa.id,
            endereco="Rua A, 1",
            bairro="Asa Norte",
            cidade="Brasília",
            estado="DF",
        )
        db_session.add(endereco)
        await db_session.commit()

        response = await client.get(
            "/api/v1/consultas/?q=Te&tipo=pessoa&bairro=Asa+Norte",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pessoas"]) >= 1
        pessoa_data = next(p for p in data["pessoas"] if p["nome"] == "Teste Bairro")
        assert pessoa_data["endereco_criado_em"] is not None


class TestPessoasPorVeiculo:
    """Testes do endpoint GET /api/v1/consultas/pessoas-por-veiculo."""

    async def test_pessoas_por_veiculo_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que requisição sem autenticação retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/consultas/pessoas-por-veiculo?placa=ABC")
        assert response.status_code == 401

    async def test_pessoas_por_veiculo_sem_parametros_retorna_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que busca sem placa e sem modelo retorna 400.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/pessoas-por-veiculo",
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_pessoas_por_veiculo_com_placa_retorna_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que busca com placa retorna 200 (lista pode ser vazia).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/pessoas-por-veiculo?placa=ABC",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
