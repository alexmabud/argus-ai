"""Testes de sessão exclusiva — session_id revogado rejeita requisições."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_token_com_session_id_errado_retorna_401(client: AsyncClient, usuario, db_session):
    """Token com session_id diferente do banco deve ser rejeitado com 401.

    Args:
        client: Cliente HTTP de testes.
        usuario: Fixture de usuário de teste.
        db_session: Sessão do banco de testes.
    """
    from app.core.security import criar_access_token

    # Definir session_id no banco
    usuario.session_id = "sessao-correta"
    await db_session.flush()

    # Criar token com session_id DIFERENTE
    token = criar_access_token({"sub": str(usuario.id), "sid": "sessao-errada"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_com_session_id_correto_retorna_200(client: AsyncClient, usuario, db_session):
    """Token com session_id correto deve ser aceito.

    Args:
        client: Cliente HTTP de testes.
        usuario: Fixture de usuário de teste.
        db_session: Sessão do banco de testes.
    """
    from app.core.security import criar_access_token

    usuario.session_id = "sessao-ativa"
    await db_session.flush()

    token = criar_access_token({"sub": str(usuario.id), "sid": "sessao-ativa"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_usuario_sem_session_retorna_401(client: AsyncClient, usuario, db_session):
    """Usuário com session_id None (pausado ou sem login) deve ser rejeitado.

    Args:
        client: Cliente HTTP de testes.
        usuario: Fixture de usuário de teste.
        db_session: Sessão do banco de testes.
    """
    from app.core.security import criar_access_token

    usuario.session_id = None
    await db_session.flush()

    token = criar_access_token({"sub": str(usuario.id), "sid": "qualquer"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
