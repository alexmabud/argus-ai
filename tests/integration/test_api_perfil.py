"""Testes dos endpoints de perfil do usuário."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_atualizar_perfil_sucesso(client: AsyncClient, auth_headers, usuario, db_session):
    """Testa atualização bem-sucedida de nome e posto do perfil."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "João Silva", "posto_graduacao": "Capitão"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "João Silva"
    assert data["posto_graduacao"] == "Capitão"


@pytest.mark.asyncio
async def test_atualizar_perfil_nome_guerra(client: AsyncClient, auth_headers, usuario, db_session):
    """Testa atualização de nome de guerra no perfil."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "Agente Teste", "nome_guerra": "Silva"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome_guerra"] == "Silva"


@pytest.mark.asyncio
async def test_atualizar_perfil_posto_invalido(client: AsyncClient, auth_headers):
    """Testa rejeição de posto fora da lista oficial."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "Teste", "posto_graduacao": "General"},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_atualizar_perfil_sem_auth(client: AsyncClient):
    """Testa rejeição sem autenticação."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "Teste"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_foto_perfil(client: AsyncClient, auth_headers):
    """Testa upload de foto de perfil com mock do StorageService."""
    from io import BytesIO

    fake_url = "https://r2.example.com/avatares/abc123_foto.jpg"

    with patch("app.api.v1.auth.StorageService") as mock_storage_cls:
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = fake_url
        mock_storage._generate_key.return_value = "avatares/abc123_foto.jpg"
        mock_storage_cls.return_value = mock_storage

        response = await client.post(
            "/api/v1/auth/perfil/foto",
            files={"foto": ("foto.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["foto_url"] == fake_url
