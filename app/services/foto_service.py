"""Serviço de lógica de negócio para Foto.

Gerencia upload de fotos para S3/R2 (Cloudflare), criação de registros
no banco e listagem de fotos por pessoa ou abordagem. Fotos com tipo
"rosto" são posteriormente processadas pelo arq worker para extração
de embedding facial (512 dimensões via InsightFace).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.foto import Foto
from app.repositories.foto_repo import FotoRepository
from app.services.audit_service import AuditService
from app.services.storage_service import StorageService

if TYPE_CHECKING:
    from app.services.face_service import FaceService


class FotoService:
    """Serviço de Foto com upload S3 e registro no banco.

    Orquestra o fluxo de upload de fotos: envio para storage S3/R2,
    criação do registro no banco com metadados (tipo, coordenadas,
    vinculação a pessoa/abordagem) e log de auditoria. Fotos com
    tipo "rosto" ficam pendentes de processamento facial pelo worker.

    Segue as convenções do projeto:
    - Usa flush() ao invés de commit() (transação controlada pelo caller).
    - Registra todas as mutações via AuditService (LGPD).
    - face_processada=False indica pendência para o arq worker.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de Foto com busca por pessoa e abordagem.
        storage: Serviço de armazenamento S3/R2 (Cloudflare).
        audit: Serviço de auditoria para log de mutações (LGPD).
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de foto com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = FotoRepository(db)
        self.storage = StorageService()
        self.audit = AuditService(db)

    async def upload_foto(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        pessoa_id: int | None,
        abordagem_id: int | None,
        tipo: str,
        latitude: float | None,
        longitude: float | None,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Foto:
        """Faz upload de foto para S3 e cria registro no banco.

        Fluxo:
        1. Gera chave única e faz upload para S3/R2
        2. Cria registro Foto no banco com metadados
        3. Registra audit log da criação

        A foto é criada com face_processada=False. O arq worker processará
        fotos do tipo "rosto" assincronamente para extrair embedding facial
        (512 dimensões via InsightFace).

        Args:
            file_bytes: Conteúdo da imagem em bytes.
            filename: Nome original do arquivo.
            content_type: MIME type do arquivo (ex: "image/jpeg").
            pessoa_id: ID da pessoa associada (opcional, null para fotos de cena).
            abordagem_id: ID da abordagem associada (opcional).
            tipo: Tipo de foto ("rosto", "corpo", "placa", "cena").
            latitude: Latitude GPS da captura (opcional).
            longitude: Longitude GPS da captura (opcional).
            user_id: ID do oficial que fez o upload.
            ip_address: Endereço IP da requisição (opcional, para auditoria).
            user_agent: User-Agent do cliente (opcional, para auditoria).

        Returns:
            Foto criada com ID atribuído e URL do storage.

        Raises:
            Exception: Se falha no upload ao S3/R2.
        """
        # 1. Upload para S3/R2
        key = self.storage._generate_key("fotos", filename)
        url = await self.storage.upload(file_bytes, key, content_type)

        # 2. Criar registro Foto no banco
        foto = Foto(
            arquivo_url=url,
            tipo=tipo,
            data_hora=datetime.now(UTC),
            latitude=latitude,
            longitude=longitude,
            pessoa_id=pessoa_id,
            abordagem_id=abordagem_id,
            face_processada=False,
        )
        await self.repo.create(foto)

        # 3. Audit log
        await self.audit.log(
            usuario_id=user_id,
            acao="CREATE",
            recurso="foto",
            recurso_id=foto.id,
            detalhes={
                "tipo": tipo,
                "pessoa_id": pessoa_id,
                "abordagem_id": abordagem_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return foto

    async def listar_por_pessoa(self, pessoa_id: int) -> list[Foto]:
        """Lista todas as fotos associadas a uma pessoa.

        Retorna fotos ordenadas por data/hora decrescente (mais recentes primeiro).

        Args:
            pessoa_id: ID da pessoa para buscar fotos.

        Returns:
            Lista de Fotos da pessoa ordenadas por data_hora decrescente.
        """
        return list(await self.repo.get_by_pessoa(pessoa_id))

    async def listar_por_abordagem(self, abordagem_id: int) -> list[Foto]:
        """Lista todas as fotos associadas a uma abordagem.

        Retorna fotos ordenadas por data/hora decrescente (mais recentes primeiro).

        Args:
            abordagem_id: ID da abordagem para buscar fotos.

        Returns:
            Lista de Fotos da abordagem ordenadas por data_hora decrescente.
        """
        return list(await self.repo.get_by_abordagem(abordagem_id))

    async def buscar_por_rosto(
        self,
        image_bytes: bytes,
        face_service: FaceService,
        top_k: int = 5,
    ) -> list[dict]:
        """Busca pessoas por similaridade facial via pgvector.

        Extrai embedding facial da imagem enviada e busca fotos com
        rostos similares no banco via distância cosseno (512-dim).

        Args:
            image_bytes: Imagem com rosto para busca em bytes.
            face_service: Serviço InsightFace para extração de embedding.
            top_k: Número máximo de resultados.

        Returns:
            Lista de dicionários com foto, pessoa_id e similaridade.
            Lista vazia se nenhum rosto detectado na imagem.
        """
        embedding = face_service.extrair_embedding(image_bytes)
        if embedding is None:
            return []

        results = await self.repo.buscar_por_similaridade_facial(embedding, top_k=top_k)

        return [
            {
                "foto": row[0],
                "similaridade": round(float(row[1]), 4),
            }
            for row in results
        ]
