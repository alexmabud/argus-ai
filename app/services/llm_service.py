"""Serviço de geração de texto via LLM (Anthropic Claude ou Ollama).

Abstrai a comunicação com provedores de LLM, suportando Anthropic
Claude (produção) e Ollama (desenvolvimento local). Usado pelo
RAGService para gerar relatórios operacionais a partir de contexto
recuperado.
"""

import logging

import httpx

from app.config import settings
from app.core.exceptions import LLMIndisponivelError

logger = logging.getLogger("argus")


class LLMService:
    """Serviço de geração de texto com suporte multi-provider.

    Abstrai comunicação com Anthropic Claude API ou Ollama local,
    selecionando o provedor conforme settings.LLM_PROVIDER.
    Não importa ou depende de FastAPI.

    Attributes:
        provider: Provedor selecionado ("anthropic" ou "ollama").
    """

    def __init__(self):
        """Inicializa o serviço LLM com configurações do provedor."""
        self.provider = settings.LLM_PROVIDER

    async def gerar(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Gera texto a partir de prompt usando o provedor configurado.

        Despacha para _gerar_anthropic ou _gerar_ollama conforme
        settings.LLM_PROVIDER.

        Args:
            prompt: Prompt do usuário para geração.
            system: Prompt de sistema (instruções e contexto).
            max_tokens: Número máximo de tokens na resposta.

        Returns:
            Texto gerado pelo LLM.

        Raises:
            LLMIndisponivelError: Se o provedor está indisponível ou retorna erro.
        """
        if self.provider == "anthropic":
            return await self._gerar_anthropic(prompt, system, max_tokens)
        if self.provider == "ollama":
            return await self._gerar_ollama(prompt, system)
        raise LLMIndisponivelError(f"Provedor LLM não suportado: {self.provider}")

    async def _gerar_anthropic(
        self,
        prompt: str,
        system: str,
        max_tokens: int,
    ) -> str:
        """Gera texto via Anthropic Claude API.

        Faz requisição POST para a API de mensagens da Anthropic usando
        httpx assíncrono. Modelo padrão: claude-sonnet-4-20250514.

        Args:
            prompt: Prompt do usuário.
            system: Prompt de sistema.
            max_tokens: Máximo de tokens na resposta.

        Returns:
            Texto gerado pelo Claude.

        Raises:
            LLMIndisponivelError: Se a API está indisponível ou retorna erro.
        """
        try:
            async with httpx.AsyncClient() as client:
                body: dict = {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    body["system"] = system

                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            logger.error("Anthropic API error: %s", e.response.text)
            raise LLMIndisponivelError(f"Erro na API Anthropic: {e.response.status_code}")
        except Exception as e:
            logger.error("Anthropic connection error: %s", str(e))
            raise LLMIndisponivelError("Não foi possível conectar à API Anthropic")

    async def _gerar_ollama(self, prompt: str, system: str) -> str:
        """Gera texto via Ollama local.

        Faz requisição POST para o servidor Ollama local usando httpx
        assíncrono. Modelo configurado em settings.OLLAMA_MODEL.

        Args:
            prompt: Prompt do usuário.
            system: Prompt de sistema.

        Returns:
            Texto gerado pelo modelo Ollama.

        Raises:
            LLMIndisponivelError: Se o servidor Ollama está indisponível.
        """
        try:
            async with httpx.AsyncClient() as client:
                body: dict = {
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                }
                if system:
                    body["system"] = system

                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json=body,
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["response"]
        except Exception as e:
            logger.error("Ollama connection error: %s", str(e))
            raise LLMIndisponivelError("Servidor Ollama indisponível")
