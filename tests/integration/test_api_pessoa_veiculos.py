"""Testes de integração para endpoints de vínculo direto pessoa-veículo.

Testa criação, listagem unificada (direto + via abordagem) e remoção
de vínculos diretos entre pessoa e veículo, incluindo autenticação e
isolamento multi-tenant.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo


class TestVincularVeiculo:
    """Testes do endpoint POST /api/v1/pessoas/{id}/veiculos/{veiculo_id}."""

    async def test_vincula_retorna_201(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que vincular veículo retorna 201 com dados corretos.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["veiculo_id"] == veiculo.id
        assert data["placa"] == veiculo.placa
        assert data["origem"] == "direto"

    async def test_vincular_duplicado_retorna_409(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que vincular o mesmo par duas vezes retorna 409.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        assert response.status_code == 409

    async def test_vincular_sem_auth_retorna_401(
        self, client: AsyncClient, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assíncrono.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        response = await client.post(f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}")
        assert response.status_code == 401


class TestListarVeiculosPessoa:
    """Testes do endpoint GET /api/v1/pessoas/{id}/veiculos."""

    async def test_lista_veiculo_vinculado_direto(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que veículo vinculado diretamente aparece na listagem.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        response = await client.get(f"/api/v1/pessoas/{pessoa.id}/veiculos", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["origem"] == "direto"
        assert data[0]["veiculo_id"] == veiculo.id

    async def test_lista_vazia_quando_sem_vinculo(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa
    ):
        """Testa que listagem retorna vazio quando não há veículo vinculado.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.get(f"/api/v1/pessoas/{pessoa.id}/veiculos", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_listar_sem_auth_retorna_401(self, client: AsyncClient, pessoa: Pessoa):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assíncrono.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.get(f"/api/v1/pessoas/{pessoa.id}/veiculos")
        assert response.status_code == 401


class TestDesvincularVeiculo:
    """Testes do endpoint DELETE /api/v1/pessoas/{id}/veiculos/{veiculo_id}."""

    async def test_desvincular_retorna_204_e_some_da_lista(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que desvincular retorna 204 e o veículo some da listagem.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        assert response.status_code == 204

        listagem = await client.get(f"/api/v1/pessoas/{pessoa.id}/veiculos", headers=auth_headers)
        assert listagem.json() == []

    async def test_desvincular_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que desvincular par nunca vinculado retorna 404.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_desvincular_sem_auth_retorna_401(
        self, client: AsyncClient, pessoa: Pessoa, veiculo: Veiculo
    ):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assíncrono.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        response = await client.delete(f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}")
        assert response.status_code == 401

    async def test_desvincular_por_outro_usuario_retorna_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_outro_usuario: dict,
        pessoa: Pessoa,
        veiculo: Veiculo,
    ):
        """Testa que usuário que não criou o vínculo nem é admin recebe 403.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers do usuário que criou o vínculo.
            auth_headers_outro_usuario: Headers de um segundo usuário da mesma
                guarnição, sem privilégio de admin.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}",
            headers=auth_headers_outro_usuario,
        )
        assert response.status_code == 403

    async def test_desvincular_por_admin_retorna_204(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_admin: dict,
        pessoa: Pessoa,
        veiculo: Veiculo,
    ):
        """Testa que admin da guarnição pode desvincular vínculo criado por outro usuário.

        Args:
            client: Cliente HTTP assíncrono.
            auth_headers: Headers do usuário que criou o vínculo (não-admin).
            auth_headers_admin: Headers de um admin da mesma guarnição.
            pessoa: Fixture de pessoa da guarnição.
            veiculo: Fixture de veículo da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers
        )
        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo.id}", headers=auth_headers_admin
        )
        assert response.status_code == 204


class TestPessoaVeiculoCrossTenant:
    """Testes de isolamento cross-tenant para vínculo direto pessoa-veículo."""

    async def _criar_tenant_b(self, db_session: AsyncSession) -> tuple[Guarnicao, Veiculo]:
        """Cria guarnição, usuário e veículo de um segundo tenant (B).

        Args:
            db_session: Sessão do banco de teste.

        Returns:
            Tupla (guarnicao_b, veiculo_b).
        """
        bpm_b = Bpm(nome="5o BPM Veiculos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(
            nome="5a Cia - GU 02",
            bpm_id=bpm_b.id,
            codigo="5BPM-5CIA-GU02-VEIC",
        )
        db_session.add(guarnicao_b)
        await db_session.flush()

        veiculo_b = Veiculo(placa="XYZ9K88", guarnicao_id=guarnicao_b.id)
        db_session.add(veiculo_b)
        await db_session.flush()

        return guarnicao_b, veiculo_b

    async def test_nao_pode_vincular_veiculo_de_outro_tenant(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        pessoa: Pessoa,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que operador não pode vincular veículo de outra guarnição.

        Um operador autenticado na guarnição A não deve conseguir vincular
        à pessoa da guarnição A um veículo pertencente à guarnição B.

        Args:
            client: Cliente HTTP assíncrono.
            db_session: Sessão do banco de teste.
            pessoa: Fixture de pessoa da guarnição principal (tenant A).
            guarnicao: Guarnição principal (tenant A).
            usuario: Usuário autenticado da guarnição principal (tenant A).
        """
        _, veiculo_b = await self._criar_tenant_b(db_session)

        token_a = criar_access_token(
            {"sub": str(usuario.id), "guarnicao_id": guarnicao.id, "sid": usuario.session_id}
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/veiculos/{veiculo_b.id}", headers=headers_a
        )
        assert response.status_code in (403, 404)

    async def test_nao_pode_vincular_veiculo_a_pessoa_de_outro_tenant(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        veiculo: Veiculo,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que operador não pode vincular veículo a pessoa de outra guarnição.

        Args:
            client: Cliente HTTP assíncrono.
            db_session: Sessão do banco de teste.
            veiculo: Fixture de veículo da guarnição principal (tenant A).
            guarnicao: Guarnição principal (tenant A).
            usuario: Usuário autenticado da guarnição principal (tenant A).
        """
        guarnicao_b, _ = await self._criar_tenant_b(db_session)
        pessoa_b = Pessoa(nome="Pessoa Outro Tenant", guarnicao_id=guarnicao_b.id)
        db_session.add(pessoa_b)
        await db_session.flush()

        token_a = criar_access_token(
            {"sub": str(usuario.id), "guarnicao_id": guarnicao.id, "sid": usuario.session_id}
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        response = await client.post(
            f"/api/v1/pessoas/{pessoa_b.id}/veiculos/{veiculo.id}", headers=headers_a
        )
        assert response.status_code in (403, 404)

    async def test_nao_pode_listar_veiculos_de_pessoa_de_outro_tenant(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Testa que operador não pode listar veículos de pessoa de outra guarnição.

        Args:
            client: Cliente HTTP assíncrono.
            db_session: Sessão do banco de teste.
            guarnicao: Guarnição principal (tenant A).
            usuario: Usuário autenticado da guarnição principal (tenant A).
        """
        guarnicao_b, _ = await self._criar_tenant_b(db_session)
        pessoa_b = Pessoa(nome="Pessoa Outro Tenant", guarnicao_id=guarnicao_b.id)
        db_session.add(pessoa_b)
        await db_session.flush()

        token_a = criar_access_token(
            {"sub": str(usuario.id), "guarnicao_id": guarnicao.id, "sid": usuario.session_id}
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        response = await client.get(f"/api/v1/pessoas/{pessoa_b.id}/veiculos", headers=headers_a)
        assert response.status_code in (403, 404)
