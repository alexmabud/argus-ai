"""Testes unitários do NotificationService (alertas Telegram)."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_enviar_noop_quando_token_vazio():
    """enviar() com TELEGRAM_BOT_TOKEN vazio não faz HTTP e retorna sem erro."""
    with patch("app.services.notification_service.settings") as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = ""
        mock_settings.TELEGRAM_CHAT_ID = "-123"

        with patch("httpx.AsyncClient") as mock_client_cls:
            from app.services.notification_service import enviar

            await enviar("teste")

        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_enviar_noop_quando_chat_id_vazio():
    """enviar() com TELEGRAM_CHAT_ID vazio não faz HTTP e retorna sem erro."""
    with patch("app.services.notification_service.settings") as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = "token123"
        mock_settings.TELEGRAM_CHAT_ID = ""

        with patch("httpx.AsyncClient") as mock_client_cls:
            from app.services.notification_service import enviar

            await enviar("teste")

        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_enviar_chama_telegram_quando_configurado():
    """enviar() com token e chat_id configura chama o endpoint correto."""
    mock_resp = AsyncMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200

    mock_post = AsyncMock(return_value=mock_resp)

    with patch("app.services.notification_service.settings") as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = "BOT_TOKEN"
        mock_settings.TELEGRAM_CHAT_ID = "CHAT_ID"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.notification_service import enviar

            await enviar("mensagem de teste")

        url_chamada = mock_post.call_args[0][0]
        assert "BOT_TOKEN" in url_chamada
        assert "sendMessage" in url_chamada


@pytest.mark.asyncio
async def test_enviar_engole_excecao_de_rede():
    """enviar() absorve exceções de rede sem propagar para o chamador."""
    with patch("app.services.notification_service.settings") as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = "token"
        mock_settings.TELEGRAM_CHAT_ID = "chat"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=ConnectionError("falha de rede"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.notification_service import enviar

            # Não deve levantar exceção
            await enviar("teste")
