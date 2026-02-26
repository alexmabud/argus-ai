"""Serviço RAG (Retrieval-Augmented Generation) para relatórios operacionais.

Implementa pipeline completo de RAG: recuperação de contexto semântico
(ocorrências + legislação) via pgvector, montagem de prompt com regras
estritas de veracidade, e geração de relatório via LLM.
"""

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NaoEncontradoError
from app.models.abordagem import Abordagem
from app.repositories.legislacao_repo import LegislacaoRepository
from app.repositories.ocorrencia_repo import OcorrenciaRepository
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

logger = logging.getLogger("argus")

SYSTEM_PROMPT = """Você é o Argus AI, assistente de inteligência policial.
Gere relatórios operacionais APENAS com base nos dados fornecidos.

REGRAS ESTRITAS:
- NUNCA invente fatos, nomes, datas ou circunstâncias.
- Se não houver dados suficientes, diga explicitamente.
- Cite as fontes (número de ocorrência ou artigo de lei) quando relevante.
- Use linguagem técnica policial brasileira.
- Estruture o relatório: CONTEXTO, ANÁLISE, LEGISLAÇÃO APLICÁVEL, RECOMENDAÇÕES.
"""


class RAGService:
    """Serviço RAG para geração de relatórios operacionais com IA.

    Orquestra pipeline completo: embed query → busca semântica em
    ocorrências e legislação → montagem de contexto → geração via LLM.
    Nunca inventa fatos — apenas organiza dados existentes.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        embedding_service: Serviço de embedding para vetorização.
        llm_service: Serviço de geração de texto via LLM.
        ocorrencia_repo: Repositório de ocorrências com busca semântica.
        legislacao_repo: Repositório de legislação com busca semântica.
    """

    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService):
        """Inicializa serviço RAG com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
            embedding_service: Serviço de embedding carregado.
        """
        self.db = db
        self.embedding_service = embedding_service
        self.llm_service = LLMService()
        self.ocorrencia_repo = OcorrenciaRepository(db)
        self.legislacao_repo = LegislacaoRepository(db)

    async def buscar_contexto(
        self,
        query: str,
        guarnicao_id: int,
        top_k: int = 5,
    ) -> list[dict]:
        """Busca ocorrências semanticamente similares à query.

        Gera embedding da query e busca no pgvector com filtro
        multi-tenant e threshold de similaridade.

        Args:
            query: Texto de busca em linguagem natural.
            guarnicao_id: ID da guarnição (multi-tenant).
            top_k: Número máximo de resultados.

        Returns:
            Lista de dicionários com ocorrência e score de similaridade.
        """
        embedding = await self.embedding_service.gerar_embedding_cached(query)
        results = await self.ocorrencia_repo.search_semantic(embedding, guarnicao_id, top_k=top_k)
        return [
            {
                "ocorrencia": row[0],
                "similaridade": round(float(row[1]), 4),
            }
            for row in results
        ]

    async def buscar_legislacao(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict]:
        """Busca legislação semanticamente similar à query.

        Args:
            query: Texto de busca em linguagem natural.
            top_k: Número máximo de resultados.

        Returns:
            Lista de dicionários com legislação e score de similaridade.
        """
        embedding = await self.embedding_service.gerar_embedding_cached(query)
        results = await self.legislacao_repo.search_semantic(embedding, top_k=top_k)
        return [
            {
                "legislacao": row[0],
                "similaridade": round(float(row[1]), 4),
            }
            for row in results
        ]

    async def gerar_relatorio(
        self,
        abordagem_id: int,
        instrucao: str,
        guarnicao_id: int,
        usuario_id: int,
    ) -> dict:
        """Gera relatório operacional completo via pipeline RAG.

        Pipeline:
        1. Carrega dados da abordagem (pessoas, veículos, passagens)
        2. Busca ocorrências similares (top-5, similaridade > 0.3)
        3. Busca legislação relevante (top-3)
        4. Monta prompt com regras estritas de veracidade
        5. Gera texto via LLM
        6. Retorna relatório + fontes + métricas

        Args:
            abordagem_id: ID da abordagem alvo.
            instrucao: Instrução adicional do usuário.
            guarnicao_id: ID da guarnição (multi-tenant).
            usuario_id: ID do usuário solicitante.

        Returns:
            Dicionário com:
            - relatorio: Texto gerado pelo LLM.
            - fontes_ocorrencias: Ocorrências usadas como contexto.
            - fontes_legislacao: Artigos de lei referenciados.
            - metricas: Tempo de execução e contagem de fontes.

        Raises:
            NaoEncontradoError: Se abordagem não existe ou não pertence
                à guarnição do usuário.
        """
        start = time.time()

        # 1. Carregar abordagem com relacionamentos
        abordagem = await self._carregar_abordagem(abordagem_id, guarnicao_id)

        # 2. Montar descrição textual da abordagem
        descricao = self._descrever_abordagem(abordagem)

        # 3. Buscar ocorrências similares
        ocorrencias_ctx = await self.buscar_contexto(descricao, guarnicao_id, top_k=5)

        # 4. Buscar legislação relevante
        legislacao_ctx = await self.buscar_legislacao(descricao, top_k=3)

        # 5. Montar prompt
        prompt = self._montar_prompt(
            abordagem, descricao, ocorrencias_ctx, legislacao_ctx, instrucao
        )

        # 6. Gerar via LLM
        relatorio = await self.llm_service.gerar(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=2000,
        )

        elapsed = round(time.time() - start, 2)

        # 7. Montar resposta
        fontes_oc = [
            {
                "id": item["ocorrencia"].id,
                "numero_ocorrencia": item["ocorrencia"].numero_ocorrencia,
                "similaridade": item["similaridade"],
            }
            for item in ocorrencias_ctx
        ]
        fontes_leg = [
            {
                "id": item["legislacao"].id,
                "lei": item["legislacao"].lei,
                "artigo": item["legislacao"].artigo,
                "nome": item["legislacao"].nome,
                "similaridade": item["similaridade"],
            }
            for item in legislacao_ctx
        ]

        logger.info(
            "Relatório gerado para abordagem %d em %.2fs (%d ocorrências, %d legislações)",
            abordagem_id,
            elapsed,
            len(fontes_oc),
            len(fontes_leg),
        )

        return {
            "relatorio": relatorio,
            "fontes_ocorrencias": fontes_oc,
            "fontes_legislacao": fontes_leg,
            "metricas": {
                "tempo_geracao_s": elapsed,
                "total_fontes_ocorrencias": len(fontes_oc),
                "total_fontes_legislacao": len(fontes_leg),
            },
        }

    async def _carregar_abordagem(self, abordagem_id: int, guarnicao_id: int) -> Abordagem:
        """Carrega abordagem com eager load de relacionamentos.

        Args:
            abordagem_id: ID da abordagem.
            guarnicao_id: ID da guarnição (verificação multi-tenant).

        Returns:
            Abordagem com pessoas, veículos e passagens carregados.

        Raises:
            NaoEncontradoError: Se abordagem não encontrada ou não pertence
                à guarnição.
        """
        from sqlalchemy import select

        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas),
                selectinload(Abordagem.veiculos),
                selectinload(Abordagem.passagens),
            )
            .where(
                Abordagem.id == abordagem_id,
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        abordagem = result.scalar_one_or_none()

        if abordagem is None:
            raise NaoEncontradoError("Abordagem não encontrada")
        return abordagem

    def _descrever_abordagem(self, abordagem: Abordagem) -> str:
        """Gera descrição textual da abordagem para embedding.

        Combina informações de pessoas, veículos e observações em um
        texto único para gerar embedding de busca.

        Args:
            abordagem: Abordagem com relacionamentos carregados.

        Returns:
            Texto descritivo da abordagem.
        """
        partes = []

        if abordagem.observacoes:
            partes.append(f"Observações: {abordagem.observacoes}")

        for ap in abordagem.pessoas:
            pessoa = ap.pessoa
            if pessoa:
                partes.append(f"Pessoa abordada: {pessoa.nome}")

        for av in abordagem.veiculos:
            veiculo = av.veiculo
            if veiculo:
                info = f"Veículo: {veiculo.placa}"
                if veiculo.modelo:
                    info += f" ({veiculo.modelo})"
                partes.append(info)

        return ". ".join(partes) if partes else "Abordagem policial"

    def _montar_prompt(
        self,
        abordagem: Abordagem,
        descricao: str,
        ocorrencias_ctx: list[dict],
        legislacao_ctx: list[dict],
        instrucao: str,
    ) -> str:
        """Monta prompt completo para geração do relatório via LLM.

        Estrutura o prompt com dados da abordagem, contexto de ocorrências
        similares e legislação relevante. Inclui instrução do usuário se
        fornecida.

        Args:
            abordagem: Abordagem alvo.
            descricao: Descrição textual da abordagem.
            ocorrencias_ctx: Ocorrências similares encontradas.
            legislacao_ctx: Legislação relevante encontrada.
            instrucao: Instrução adicional do usuário.

        Returns:
            Prompt formatado para o LLM.
        """
        sections = [f"## Abordagem #{abordagem.id}\n{descricao}"]

        # Ocorrências similares
        if ocorrencias_ctx:
            lines = ["## Ocorrências Similares"]
            for item in ocorrencias_ctx:
                oc = item["ocorrencia"]
                sim = item["similaridade"]
                texto = (oc.texto_extraido or "")[:500]
                lines.append(f"- BO {oc.numero_ocorrencia} (similaridade: {sim}): {texto}")
            sections.append("\n".join(lines))

        # Legislação
        if legislacao_ctx:
            lines = ["## Legislação Aplicável"]
            for item in legislacao_ctx:
                leg = item["legislacao"]
                sim = item["similaridade"]
                lines.append(
                    f"- {leg.lei} Art. {leg.artigo}"
                    f" ({leg.nome or 'sem nome'}, similaridade: {sim}): {leg.texto[:300]}"
                )
            sections.append("\n".join(lines))

        # Instrução do usuário
        if instrucao:
            sections.append(f"## Instrução Adicional\n{instrucao}")

        sections.append(
            "## Tarefa\nGere um relatório operacional estruturado com base "
            "EXCLUSIVAMENTE nos dados acima."
        )

        return "\n\n".join(sections)
