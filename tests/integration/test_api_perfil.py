"""Testes dos endpoints de perfil do usuário."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image


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
    assert data["nome"] == "JOÃO SILVA"
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
    assert data["nome_guerra"] == "SILVA"


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
async def test_atualizar_perfil_ignora_campos_de_privilegio(
    client: AsyncClient, auth_headers, usuario, db_session
):
    """PUT /perfil não deixa o próprio usuário se promover a admin (achado #31/2026-07-13).

    PerfilUpdate não declara is_admin/is_super_admin/guarnicao_id — Pydantic
    descarta silenciosamente qualquer campo extra no JSON (mass assignment
    protegido por whitelist de schema), e o endpoint faz atribuição campo a
    campo, nunca um unpacking genérico do payload sobre o model. Este teste
    prova isso na prática, não só por inspeção do schema.
    """
    assert usuario.is_admin is False
    assert usuario.is_super_admin is False
    guarnicao_original = usuario.guarnicao_id

    response = await client.put(
        "/api/v1/auth/perfil",
        json={
            "nome": "Agente Teste",
            "is_admin": True,
            "is_super_admin": True,
            "guarnicao_id": 999999,
            "admin_global": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    await db_session.refresh(usuario)
    assert usuario.is_admin is False
    assert usuario.is_super_admin is False
    assert usuario.guarnicao_id == guarnicao_original


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
        mock_storage.generate_key.return_value = "avatares/abc123_foto.jpg"
        mock_storage_cls.return_value = mock_storage
        mock_storage_cls.get.return_value = mock_storage

        response = await client.post(
            "/api/v1/auth/perfil/foto",
            files={"foto": ("foto.jpg", BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 16), "image/jpeg")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["foto_url"] == fake_url


@pytest.mark.asyncio
async def test_upload_foto_perfil_rejeita_dimensoes_excessivas(client: AsyncClient, auth_headers):
    """Upload de avatar com dimensões acima do teto é rejeitado (revisão pós-#17/2026-07-13).

    validar_dimensoes_imagem (decompression-bomb guard) tinha sido aplicada
    em todos os uploads de fotos.py, mas o upload de avatar em auth.py foi
    esquecido — este teste prova que o endpoint agora chama a validação.
    """
    from app.core.upload_validation import MAX_IMAGE_PIXELS

    lado = int(MAX_IMAGE_PIXELS**0.5) + 100
    img = Image.new("RGB", (lado, lado), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    with patch("app.api.v1.auth.StorageService"):
        response = await client.post(
            "/api/v1/auth/perfil/foto",
            files={"foto": ("foto.jpg", buf.getvalue(), "image/jpeg")},
            headers=auth_headers,
        )

    assert response.status_code == 400
