"""Testes de integração da API de Ocorrências.

Testa endpoints de busca de ocorrências por nome, número RAP e data.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocorrencia import Ocorrencia


class TestBuscarOcorrencias:
    """Testes do endpoint GET /api/v1/ocorrencias/buscar."""

    async def test_busca_por_nome_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome encontra ocorrência com esse nome no texto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com texto contendo "Carlos Eduardo".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Carlos Eduardo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_rap_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por número RAP parcial retorna a ocorrência correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com número "RAP 2026/000001".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?rap=2026/000001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_data_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por data de criação retorna ocorrência correta.

        Usa data UTC para coincidir com o timestamp armazenado pelo banco,
        que opera em UTC independente do fuso local do cliente.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência criada hoje.
        """
        from datetime import UTC, datetime

        hoje_utc = datetime.now(UTC).date().isoformat()
        response = await client.get(
            f"/api/v1/ocorrencias/buscar?data={hoje_utc}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_busca_sem_filtros_retorna_lista_vazia(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que busca sem filtros retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_nome_inexistente_retorna_vazio(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome que não existe retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência (garante dado no banco).
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=NomeQueNaoExiste",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_sem_auth_retorna_401(self, client: AsyncClient):
        """Testa que busca sem autenticação retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/ocorrencias/buscar?nome=Carlos")
        assert response.status_code == 401

    async def test_busca_por_nome_em_nomes_envolvidos(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        guarnicao,
        usuario,
    ):
        """Testa que busca por nome encontra ocorrência pelo campo nomes_envolvidos.

        Cria ocorrência SEM texto extraído mas COM nomes_envolvidos,
        e verifica que a busca por nome a encontra.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão do banco de dados.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import date

        from app.models.ocorrencia import Ocorrencia

        oc = Ocorrencia(
            numero_ocorrencia="RAP 2026/000002",
            arquivo_pdf_url="https://r2.example.com/pdfs/test2.pdf",
            nomes_envolvidos="Fulano de Tal|Ciclano Silva",
            processada=False,
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
            data_ocorrencia=date.today(),
        )
        db_session.add(oc)
        await db_session.flush()

        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Fulano de Tal",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000002"
        assert "Fulano de Tal" in data[0]["nomes_envolvidos"]

    async def test_busca_nao_retorna_ocorrencia_de_outra_guarnicao(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        ocorrencia: Ocorrencia,
    ):
        """Testa que busca não retorna ocorrências de outra guarnição.

        Cria uma segunda guarnição com usuário e ocorrência própria,
        e verifica que a busca da primeira guarnição não retorna dados da segunda.

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de dados.
            auth_headers: Headers com Bearer token da primeira guarnição.
            ocorrencia: Fixture de ocorrência da primeira guarnição.
        """
        from app.core.security import hash_senha
        from app.models.guarnicao import Guarnicao
        from app.models.ocorrencia import Ocorrencia
        from app.models.usuario import Usuario

        # Segunda guarnição com ocorrência própria
        guarnicao2 = Guarnicao(nome="2a Cia - GU 02", unidade="2o BPM", codigo="2BPM-2CIA-GU02")
        db_session.add(guarnicao2)
        await db_session.flush()

        usuario2 = Usuario(
            nome="Agente Dois",
            matricula="TEST002",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao2.id,
        )
        db_session.add(usuario2)
        await db_session.flush()

        # Cria abordagem para a segunda guarnição
        from datetime import UTC, datetime

        from app.models.abordagem import Abordagem

        abordagem2 = Abordagem(
            data_hora=datetime.now(UTC),
            guarnicao_id=guarnicao2.id,
            usuario_id=usuario2.id,
        )
        db_session.add(abordagem2)
        await db_session.flush()

        from datetime import date as date_type

        oc2 = Ocorrencia(
            numero_ocorrencia="RAP 2026/999999",
            abordagem_id=abordagem2.id,
            arquivo_pdf_url="https://r2.example.com/pdfs/outra.pdf",
            texto_extraido="Carlos Eduardo Souza na segunda guarnição.",
            processada=True,
            usuario_id=usuario2.id,
            guarnicao_id=guarnicao2.id,
            data_ocorrencia=date_type.today(),
        )
        db_session.add(oc2)
        await db_session.flush()

        # Busca pela primeira guarnição (auth_headers pertence à guarnicao 1)
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Carlos Eduardo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Deve retornar apenas a ocorrência da primeira guarnição
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"
