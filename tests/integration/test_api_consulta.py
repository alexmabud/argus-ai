"""Testes de integração da API de Consulta Unificada.

Testa endpoint de busca cross-domain em pessoas, veículos
e abordagens através de um único termo de busca.
Também testa o endpoint de busca de pessoas por veículo.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario


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

    async def test_consulta_q_so_whitespace_retorna_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Termo só com espaços não pode passar como busca válida (#2 auditoria).

        `q="  "` tem len==2 e burlava o gate len(q) < 2, normalizando para
        vazio e gerando ILIKE '%%' global. Deve ser rejeitado com 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/?q=%20%20",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_consulta_q_normaliza_vazio_nao_casa_tudo(
        self, client: AsyncClient, auth_headers: dict, veiculo
    ):
        """Termo que normaliza para vazio não pode virar ILIKE '%%' (#2 auditoria).

        `q="--"` passa o gate len>=2, mas a placa normaliza para '' (sem traços).
        A guarda do repositório deve impedir o match-all, retornando veículos vazio
        mesmo havendo um veículo cadastrado (fixture `veiculo`).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            veiculo: Veículo de teste (placa ABC1D23).
        """
        response = await client.get(
            "/api/v1/consultas/?q=--&tipo=veiculo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["veiculos"] == []

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

    async def test_pessoas_por_veiculo_placa_so_whitespace_retorna_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Placa só com espaços não é busca válida (#2 auditoria).

        `placa="  "` é truthy e burlava o gate `if not placa`, normalizando
        para vazio e gerando ILIKE '%%'. Deve ser rejeitado com 400.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/consultas/pessoas-por-veiculo?placa=%20%20",
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


@pytest.fixture
async def equipe_c(db_session: AsyncSession, bpm) -> Guarnicao:
    """Equipe C para testes de isolamento de consulta.

    Args:
        db_session: Sessão do banco de dados.
        bpm: BPM pai da equipe.

    Returns:
        Guarnicao: Guarnição Charlie com isolamento_abordagens=False.
    """
    g = Guarnicao(nome="GU Charlie", bpm_id=bpm.id, codigo="3BPM-GUC")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_c(db_session: AsyncSession, equipe_c: Guarnicao) -> Usuario:
    """Usuário pertencente à equipe C.

    Args:
        db_session: Sessão do banco de dados.
        equipe_c: Guarnição Charlie.

    Returns:
        Usuario: Usuário da equipe C com matrícula CCC001.
    """
    u = Usuario(
        nome="Agente C",
        matricula="CCC001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=equipe_c.id,
        session_id="session-c",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_c(usuario_c: Usuario) -> dict:
    """Headers de autenticação do usuário da equipe C.

    Args:
        usuario_c: Usuário da equipe C.

    Returns:
        dict: Headers com Authorization Bearer token do usuário C.
    """
    token = criar_access_token(
        {
            "sub": str(usuario_c.id),
            "guarnicao_id": usuario_c.guarnicao_id,
            "sid": usuario_c.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestConsultaIsolamento:
    """Pessoas são sempre globais; abordagens respeitam o toggle de isolamento."""

    async def test_pessoas_sempre_visiveis_para_outra_equipe(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        headers_c: dict,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Busca de pessoa retorna resultados de outra equipe (pessoas são sempre globais).

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de dados.
            headers_c: Headers do usuário da equipe C.
            guarnicao: Equipe A (padrão do conftest).
            usuario: Usuário da equipe A.
        """
        p = Pessoa(nome="Joao Testador Global", guarnicao_id=guarnicao.id)
        db_session.add(p)
        await db_session.flush()

        response = await client.get(
            "/api/v1/consultas/?q=Joao+Testador&tipo=pessoa",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        nomes = [pessoa["nome"] for pessoa in data["pessoas"]]
        assert "Joao Testador Global" in nomes

    async def test_abordagens_toggle_off_ve_global(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        headers_c: dict,
        guarnicao: Guarnicao,
        usuario: Usuario,
        equipe_c: Guarnicao,
    ):
        """Busca de abordagem com toggle OFF retorna resultados de outra equipe.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de dados.
            headers_c: Headers do usuário da equipe C.
            guarnicao: Equipe A (padrão do conftest).
            usuario: Usuário da equipe A.
            equipe_c: Equipe C (toggle OFF por padrão).
        """
        a = Abordagem(
            guarnicao_id=guarnicao.id,
            usuario_id=usuario.id,
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Global Consulta Teste",
        )
        db_session.add(a)
        await db_session.flush()

        assert equipe_c.isolamento_abordagens is False
        response = await client.get(
            "/api/v1/consultas/?q=Global+Consulta&tipo=abordagem",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["abordagens"]) >= 1

    async def test_abordagens_toggle_on_nao_ve_outra_equipe(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        headers_c: dict,
        guarnicao: Guarnicao,
        usuario: Usuario,
        equipe_c: Guarnicao,
    ):
        """Busca de abordagem com toggle ON não retorna resultados de outra equipe.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de dados.
            headers_c: Headers do usuário da equipe C.
            guarnicao: Equipe A (padrão do conftest).
            usuario: Usuário da equipe A.
            equipe_c: Equipe C (toggle será ativado).
        """
        a = Abordagem(
            guarnicao_id=guarnicao.id,
            usuario_id=usuario.id,
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Isolada Consulta Teste",
        )
        db_session.add(a)
        await db_session.flush()

        equipe_c.isolamento_abordagens = True
        await db_session.flush()

        response = await client.get(
            "/api/v1/consultas/?q=Isolada+Consulta&tipo=abordagem",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["abordagens"]) == 0


class TestConsultaAudit:
    """Testes de auditoria de consultas (Fase C2 — LGPD)."""

    async def test_consulta_unificada_gera_audit_search(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        usuario: Usuario,
    ):
        """Consulta unificada deve gerar registro de auditoria acao=SEARCH.

        O termo de busca não deve aparecer em claro nos detalhes (LGPD).

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de testes.
            auth_headers: Headers com token de autenticação.
            usuario: Fixture de usuário.
        """
        from sqlalchemy import select

        from app.models.audit_log import AuditLog

        await client.get(
            "/api/v1/consultas/?q=termodeteste",
            headers=auth_headers,
        )

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.acao == "SEARCH",
                AuditLog.recurso == "consulta",
                AuditLog.usuario_id == usuario.id,
            )
        )
        registros = result.scalars().all()
        assert len(registros) >= 1
        # O termo não deve aparecer em claro nos detalhes
        detalhes = registros[0].detalhes or {}
        assert "termodeteste" not in str(detalhes)
