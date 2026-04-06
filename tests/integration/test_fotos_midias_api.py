"""Testes de integração do endpoint POST /fotos/midias."""

import io

from httpx import AsyncClient

from app.models.abordagem import Abordagem


class TestUploadMidiaAbordagem:
    """Testes do endpoint POST /fotos/midias."""

    async def test_rejeita_sem_autenticacao(self, client: AsyncClient, abordagem: Abordagem):
        """Testa que o endpoint requer autenticação.

        Args:
            client: Cliente HTTP de teste.
            abordagem: Fixture de abordagem.
        """
        pdf_bytes = b"%PDF-1.4 fake"
        files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"abordagem_id": str(abordagem.id)}
        response = await client.post("/api/v1/fotos/midias", files=files, data=data)
        assert response.status_code == 401

    async def test_rejeita_mime_nao_permitido(
        self, client: AsyncClient, auth_headers: dict, abordagem: Abordagem
    ):
        """Testa que MIME type não permitido retorna 400.

        Args:
            client: Cliente HTTP de teste.
            auth_headers: Headers com JWT válido.
            abordagem: Fixture de abordagem.
        """
        files = {"file": ("arquivo.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
        data = {"abordagem_id": str(abordagem.id)}
        response = await client.post(
            "/api/v1/fotos/midias", files=files, data=data, headers=auth_headers
        )
        assert response.status_code == 400
