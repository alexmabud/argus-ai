"""Testes unitários para o serviço de geração de texto via LLM.

Valida roteamento para Anthropic e Ollama, tratamento de erros
e exceção LLMIndisponivelError.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import LLMIndisponivelError
from app.services.llm_service import LLMService


class TestLLMService:
    """Testes para LLMService."""

    @pytest.mark.asyncio
    async def test_gerar_anthropic_sucesso(self):
        """Deve gerar texto via Anthropic quando disponível."""
        service = LLMService()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "Relatório gerado"}]}

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "test-key"

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await service._gerar_anthropic(
                    prompt="teste", system="system", max_tokens=100
                )
                assert result == "Relatório gerado"

    @pytest.mark.asyncio
    async def test_gerar_anthropic_erro_levanta_excecao(self):
        """Deve levantar LLMIndisponivelError quando Anthropic falha."""
        service = LLMService()

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "test-key"

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
                mock_client_cls.return_value = mock_client

                with pytest.raises(LLMIndisponivelError):
                    await service._gerar_anthropic(prompt="teste", system="system", max_tokens=100)

    @pytest.mark.asyncio
    async def test_gerar_roteia_para_provider(self):
        """Deve rotear para o provider correto com base em settings."""
        service = LLMService()

        with patch.object(service, "_gerar_anthropic", new_callable=AsyncMock) as mock_anthropic:
            mock_anthropic.return_value = "resultado"

            with patch("app.services.llm_service.settings") as mock_settings:
                mock_settings.LLM_PROVIDER = "anthropic"

                result = await service.gerar("prompt", "system", 100)
                assert result == "resultado"
                mock_anthropic.assert_called_once()
