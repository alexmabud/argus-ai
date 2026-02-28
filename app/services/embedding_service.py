"""Serviço de geração de embeddings vetoriais com cache Redis.

Carrega modelo SentenceTransformers multilíngue para gerar embeddings
de 384 dimensões para busca semântica. Suporta cache Redis para evitar
reprocessamento de queries repetidas.
"""

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger("argus")


class EmbeddingService:
    """Serviço de embedding vetorial com cache Redis.

    Carrega modelo paraphrase-multilingual-MiniLM-L12-v2 em memória
    e gera embeddings de 384 dimensões para textos em português.
    Suporta geração síncrona (para workers) e assíncrona com cache
    Redis (para API).

    Attributes:
        model: Instância do SentenceTransformer carregada em memória.
        redis_url: URL de conexão Redis para cache de embeddings.
        cache_ttl: TTL do cache em segundos (padrão 3600s = 1h).
    """

    def __init__(self):
        """Inicializa serviço carregando modelo de embeddings.

        Carrega o modelo SentenceTransformers definido em settings.EMBEDDING_MODEL.
        O modelo fica em memória durante todo o ciclo de vida da aplicação.
        """
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers não está instalado")
        logger.info("Carregando modelo de embeddings: %s", settings.EMBEDDING_MODEL)
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.redis_url = settings.REDIS_URL
        self.cache_ttl = settings.EMBEDDING_CACHE_TTL
        logger.info("Modelo de embeddings carregado com sucesso")

    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera embedding de um texto.

        Operação síncrona (CPU-bound) que codifica o texto em um vetor
        de 384 dimensões usando o modelo multilíngue.

        Args:
            texto: Texto para gerar embedding.

        Returns:
            Lista de 384 floats representando o vetor de embedding.
        """
        return self.model.encode(texto).tolist()

    def gerar_embeddings_batch(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings em batch para múltiplos textos.

        Mais eficiente que chamadas individuais pois aproveita
        paralelismo interno do modelo.

        Args:
            textos: Lista de textos para gerar embeddings.

        Returns:
            Lista de vetores de embedding (384 dimensões cada).
        """
        return self.model.encode(textos).tolist()

    async def gerar_embedding_cached(self, texto: str) -> list[float]:
        """Gera embedding com cache Redis para queries repetidas.

        Verifica cache Redis antes de gerar embedding. Se encontrado,
        retorna do cache. Caso contrário, gera e armazena com TTL
        configurado. Chave de cache: MD5 do texto.

        Args:
            texto: Texto para gerar embedding.

        Returns:
            Lista de 384 floats (do cache ou recém-gerado).
        """
        cache_key = f"emb:{hashlib.md5(texto.encode(), usedforsecurity=False).hexdigest()}"

        try:
            redis_client = aioredis.from_url(self.redis_url)
            cached = await redis_client.get(cache_key)
            if cached:
                await redis_client.aclose()
                return json.loads(cached)
        except Exception:
            logger.warning("Redis indisponível para cache de embeddings")
            redis_client = None

        embedding = self.gerar_embedding(texto)

        if redis_client:
            try:
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(embedding))
                await redis_client.aclose()
            except Exception:
                logger.warning("Falha ao armazenar embedding no cache Redis")

        return embedding
