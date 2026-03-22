"""Serviço de geração de texto via LLM (Anthropic ou Ollama).

Roteia chamadas para o provedor configurado em settings.LLM_PROVIDER.
Suporta Anthropic Claude (nuvem) e Ollama (local). Usado para geração
de relatórios, resumos de ocorrências e análises de abordagem via RAG.
"""

import logging

import httpx

from app.config import settings
from app.core.exceptions import LLMIndisponivelError

logger = logging.getLogger("argus")


class LLMService:
    """Serviço de geração de texto via LLM.

    Abstrai a comunicação com provedores de LLM (Anthropic e Ollama),
    permitindo alternar entre nuvem e local via configuração.
    Levanta LLMIndisponivelError em caso de falha no provedor.
    """

    async def _gerar_anthropic(self, prompt: str, system: str, max_tokens: int) -> str:
        """Gera texto via API Anthropic Claude.

        Args:
            prompt: Texto do usuário.
            system: Instrução de sistema para o modelo.
            max_tokens: Limite de tokens na resposta.

        Returns:
            Texto gerado pelo modelo.

        Raises:
            LLMIndisponivelError: Quando a API Anthropic retorna erro ou está inacessível.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                return response.json()["content"][0]["text"]
        except Exception as exc:
            logger.error("Erro ao chamar Anthropic: %s", exc)
            raise LLMIndisponivelError() from exc

    async def _gerar_ollama(self, prompt: str, system: str, max_tokens: int) -> str:
        """Gera texto via Ollama (LLM local).

        Args:
            prompt: Texto do usuário.
            system: Instrução de sistema para o modelo.
            max_tokens: Limite de tokens na resposta.

        Returns:
            Texto gerado pelo modelo.

        Raises:
            LLMIndisponivelError: Quando o servidor Ollama está inacessível.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": f"{system}\n\n{prompt}",
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                )
            return response.json()["response"]
        except Exception as exc:
            logger.error("Erro ao chamar Ollama: %s", exc)
            raise LLMIndisponivelError() from exc

    async def gerar(self, prompt: str, system: str, max_tokens: int) -> str:
        """Gera texto roteando para o provedor configurado.

        Args:
            prompt: Texto do usuário.
            system: Instrução de sistema para o modelo.
            max_tokens: Limite de tokens na resposta.

        Returns:
            Texto gerado pelo modelo.

        Raises:
            LLMIndisponivelError: Quando o provedor falha ou está inacessível.
        """
        if settings.LLM_PROVIDER == "anthropic":
            return await self._gerar_anthropic(prompt, system, max_tokens)
        return await self._gerar_ollama(prompt, system, max_tokens)
