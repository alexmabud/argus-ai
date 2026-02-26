"""Serviço de domínio para Ocorrência (boletim de ocorrência).

Gerencia o ciclo de vida de ocorrências policiais: upload de PDF para S3,
criação do registro, enfileiramento de processamento assíncrono (extração
de texto e geração de embedding via arq worker) e consultas.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.models.ocorrencia import Ocorrencia
from app.repositories.ocorrencia_repo import OcorrenciaRepository
from app.services.audit_service import AuditService
from app.services.storage_service import StorageService

logger = logging.getLogger("argus")


class OcorrenciaService:
    """Serviço de domínio para gerenciamento de ocorrências policiais.

    Orquestra criação de ocorrências (upload PDF → S3, registro em banco,
    enfileiramento para processamento), consultas com filtros multi-tenant
    e busca por número de BO.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de ocorrências com busca semântica.
        audit: Serviço de auditoria.
        storage: Serviço de armazenamento S3/R2.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço com repositório e dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = OcorrenciaRepository(db)
        self.audit = AuditService(db)
        self.storage = StorageService()

    async def criar(
        self,
        numero_ocorrencia: str,
        abordagem_id: int,
        arquivo_pdf: bytes,
        filename: str,
        usuario_id: int,
        guarnicao_id: int,
    ) -> Ocorrencia:
        """Cria nova ocorrência com upload de PDF.

        Faz upload do PDF para S3/R2, cria registro no banco (processada=False)
        e registra audit log. O processamento do PDF (extração de texto +
        embedding) é feito via arq worker em background.

        Args:
            numero_ocorrencia: Número único do BO.
            abordagem_id: ID da abordagem associada.
            arquivo_pdf: Conteúdo do PDF em bytes.
            filename: Nome original do arquivo PDF.
            usuario_id: ID do usuário que cadastrou.
            guarnicao_id: ID da guarnição (multi-tenant).

        Returns:
            Ocorrência criada com processada=False.
        """
        key = self.storage._generate_key("pdfs", filename)
        url = await self.storage.upload(arquivo_pdf, key, content_type="application/pdf")

        ocorrencia = Ocorrencia(
            numero_ocorrencia=numero_ocorrencia,
            abordagem_id=abordagem_id,
            arquivo_pdf_url=url,
            processada=False,
            usuario_id=usuario_id,
            guarnicao_id=guarnicao_id,
        )
        ocorrencia = await self.repo.create(ocorrencia)

        await self.audit.log(
            usuario_id=usuario_id,
            acao="CREATE",
            recurso="ocorrencia",
            recurso_id=ocorrencia.id,
            detalhes={"numero_ocorrencia": numero_ocorrencia},
        )

        logger.info(
            "Ocorrência %s criada (id=%d), aguardando processamento",
            numero_ocorrencia,
            ocorrencia.id,
        )
        return ocorrencia

    async def buscar_por_id(self, ocorrencia_id: int, guarnicao_id: int) -> Ocorrencia:
        """Busca ocorrência por ID com filtro multi-tenant.

        Args:
            ocorrencia_id: ID da ocorrência.
            guarnicao_id: ID da guarnição do usuário.

        Returns:
            Ocorrência encontrada.

        Raises:
            NaoEncontradoError: Se ocorrência não existe ou não pertence
                à guarnição do usuário.
        """
        ocorrencia = await self.repo.get(ocorrencia_id)
        if ocorrencia is None or not ocorrencia.ativo or ocorrencia.guarnicao_id != guarnicao_id:
            raise NaoEncontradoError("Ocorrência não encontrada")
        return ocorrencia

    async def listar(
        self,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Ocorrencia]:
        """Lista ocorrências da guarnição com paginação.

        Args:
            guarnicao_id: ID da guarnição (filtro multi-tenant).
            skip: Registros a pular.
            limit: Máximo de registros.

        Returns:
            Lista de ocorrências.
        """
        result = await self.repo.get_all(skip=skip, limit=limit, guarnicao_id=guarnicao_id)
        return list(result)
