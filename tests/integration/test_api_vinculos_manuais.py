"""Testes de integração para endpoints de vínculos manuais.

Testa criação, listagem via detalhe e remoção de vínculos manuais,
incluindo isolamento multi-tenant.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario


@pytest.fixture
async def outra_pessoa(db_session: AsyncSession, guarnicao: Guarnicao) -> Pessoa:
    """Fixture de segunda pessoa da mesma guarnição.

    Args:
        db_session: Sessão do banco de teste.
        guarnicao: Guarnição de teste.

    Returns:
        Segunda pessoa criada no banco de teste.
    """
    p = Pessoa(nome="Outra Pessoa Teste", guarnicao_id=guarnicao.id)
    db_session.add(p)
    await db_session.flush()
    return p


class TestCriarVinculoManual:
    """Testes do endpoint POST /api/v1/pessoas/{id}/vinculos-manuais."""

    async def test_criar_vinculo_sucesso(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa criação de vínculo manual retorna 201 com dados corretos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={
                "pessoa_vinculada_id": outra_pessoa.id,
                "tipo": "Irmão",
                "descricao": "Mora junto",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tipo"] == "Irmão"
        assert data["descricao"] == "Mora junto"
        assert data["pessoa_vinculada_id"] == outra_pessoa.id
        assert data["nome"] == outra_pessoa.nome
        assert "id" in data
        assert "criado_em" in data

    async def test_criar_vinculo_sem_descricao(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que descrição é opcional.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Sócio"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["descricao"] is None

    async def test_criar_vinculo_duplicado_retorna_409(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que vínculo duplicado retorna 409.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        payload = {"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"}
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json=payload,
            headers=auth_headers,
        )
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_criar_sem_auth_retorna_401(
        self,
        client: AsyncClient,
        pessoa,
        outra_pessoa,
    ):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"},
        )
        assert response.status_code == 401

    async def test_tipo_obrigatorio_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que tipo ausente retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestVinculoManualNoDetalhe:
    """Testes de vinculos_manuais em GET /api/v1/pessoas/{id}."""

    async def test_detalhe_inclui_vinculos_manuais(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que detalhe da pessoa inclui campo vinculos_manuais.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Pai"},
            headers=auth_headers,
        )
        response = await client.get(f"/api/v1/pessoas/{pessoa.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "vinculos_manuais" in data
        assert len(data["vinculos_manuais"]) == 1
        assert data["vinculos_manuais"][0]["tipo"] == "Pai"
        assert data["vinculos_manuais"][0]["nome"] == outra_pessoa.nome


class TestVinculoManualCrossTenant:
    """Testes de isolamento cross-tenant para vínculos manuais."""

    async def test_nao_pode_criar_vinculo_para_pessoa_de_outro_tenant(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        pessoa,
        guarnicao: Guarnicao,
    ):
        """Testa que operador não pode criar vínculo com pessoa de outra guarnição.

        Um operador autenticado na guarnição A não deve conseguir cadastrar
        um vínculo apontando para pessoa_vinculada_id pertencente à guarnição B.
        A API deve retornar 404 (pessoa vinculada não encontrada no tenant).

        Args:
            client: Cliente HTTP assincrónico.
            db_session: Sessão do banco de teste.
            pessoa: Fixture de pessoa da guarnição principal.
            guarnicao: Guarnição principal (tenant A).
        """
        # Criar segunda guarnição (tenant B)
        outra_guarnicao = Guarnicao(
            nome="5a Cia - GU 02",
            unidade="5o BPM",
            codigo="5BPM-5CIA-GU02",
        )
        db_session.add(outra_guarnicao)
        await db_session.flush()

        # Criar usuário e pessoa no tenant B
        usuario_b = Usuario(
            nome="Agente Outro Tenant",
            matricula="OTHER001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=outra_guarnicao.id,
        )
        db_session.add(usuario_b)
        await db_session.flush()

        pessoa_outro_tenant = Pessoa(
            nome="Pessoa Outro Tenant",
            guarnicao_id=outra_guarnicao.id,
        )
        db_session.add(pessoa_outro_tenant)
        await db_session.flush()

        # Gerar token do tenant A (operador da guarnição principal)
        token_a = criar_access_token({"sub": str(1), "guarnicao_id": guarnicao.id})
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Tentar criar vínculo da pessoa do tenant A com pessoa do tenant B
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={
                "pessoa_vinculada_id": pessoa_outro_tenant.id,
                "tipo": "Amigo",
            },
            headers=headers_a,
        )
        # Pessoa vinculada pertence a outro tenant — deve ser rejeitado
        assert response.status_code in (404, 403)


class TestRemoverVinculoManual:
    """Testes do endpoint DELETE /api/v1/pessoas/{id}/vinculos-manuais/{vid}."""

    async def test_remover_vinculo_retorna_204(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa remoção de vínculo retorna 204.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"},
            headers=auth_headers,
        )
        vinculo_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais/{vinculo_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_vinculo_removido_nao_aparece_no_detalhe(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que vínculo removido não aparece mais no detalhe.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Ex-sócio"},
            headers=auth_headers,
        )
        vinculo_id = create_resp.json()["id"]

        await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais/{vinculo_id}",
            headers=auth_headers,
        )

        detail_resp = await client.get(f"/api/v1/pessoas/{pessoa.id}", headers=auth_headers)
        vinculos = detail_resp.json()["vinculos_manuais"]
        assert all(v["id"] != vinculo_id for v in vinculos)
