"""Testes unitários para FotoService.buscar_por_rosto.

Valida enriquecimento de resultados com dados da pessoa vinculada,
incluindo cenários sem rosto detectado, com pessoa vinculada e sem.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestBuscarPorRosto:
    """Testes para FotoService.buscar_por_rosto."""

    def _make_service(self):
        """Cria instância de FotoService com db e repo mockados.

        Returns:
            FotoService com dependências mockadas.
        """
        from app.services.foto_service import FotoService

        db = AsyncMock()
        with patch("app.services.foto_service.StorageService"):
            service = FotoService(db)
        service.repo = AsyncMock()
        service.audit = AsyncMock()
        return service

    def _make_foto(
        self, foto_id: int, pessoa_id: int | None, arquivo_url: str = "http://example.com/foto.jpg"
    ):
        """Cria mock de Foto com atributos necessários.

        Args:
            foto_id: ID da foto.
            pessoa_id: ID da pessoa vinculada (ou None).
            arquivo_url: URL do arquivo de imagem.

        Returns:
            MagicMock representando uma Foto.
        """
        foto = MagicMock()
        foto.id = foto_id
        foto.pessoa_id = pessoa_id
        foto.arquivo_url = arquivo_url
        return foto

    def _make_pessoa(self, pessoa_id: int, nome: str = "João Silva"):
        """Cria mock de Pessoa com atributos necessários.

        Args:
            pessoa_id: ID da pessoa.
            nome: Nome da pessoa.

        Returns:
            MagicMock representando uma Pessoa.
        """
        pessoa = MagicMock()
        pessoa.id = pessoa_id
        pessoa.nome = nome
        pessoa.apelido = None
        pessoa.foto_principal_url = None
        pessoa.cpf_encrypted = None
        return pessoa

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_sem_rosto_retorna_vazio(self):
        """Deve retornar lista vazia quando face_service não detecta rosto.

        Quando extrair_embedding retorna None (sem rosto na imagem),
        buscar_por_rosto deve retornar [] sem acionar o repositório.
        """
        service = self._make_service()

        face_service = MagicMock()
        face_service.extrair_embedding.return_value = None

        result = await service.buscar_por_rosto(
            image_bytes=b"fake_image",
            face_service=face_service,
            top_k=5,
        )

        assert result == []
        service.repo.buscar_por_similaridade_facial.assert_not_called()

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_enriquece_com_pessoa(self):
        """Deve incluir pessoa carregada no resultado quando foto tem pessoa_id.

        Quando uma foto tem pessoa_id, o resultado deve conter a chave
        "pessoa" com a instância Pessoa carregada do banco via SELECT.
        """
        service = self._make_service()

        embedding = np.array([0.1] * 512)
        face_service = MagicMock()
        face_service.extrair_embedding.return_value = embedding

        foto = self._make_foto(foto_id=1, pessoa_id=10)
        pessoa = self._make_pessoa(pessoa_id=10, nome="Maria Oliveira")

        service.repo.buscar_por_similaridade_facial = AsyncMock(return_value=[(foto, 0.9876)])

        # Mockar db.execute para retornar a pessoa
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [pessoa]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        service.db.execute = AsyncMock(return_value=mock_result)

        results = await service.buscar_por_rosto(
            image_bytes=b"fake_image",
            face_service=face_service,
            top_k=5,
        )

        assert len(results) == 1
        assert results[0]["foto"] is foto
        assert results[0]["similaridade"] == 0.9876
        assert results[0]["pessoa"] is pessoa

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_sem_pessoa_vinculada(self):
        """Deve ter pessoa=None no resultado quando foto não tem pessoa_id.

        Quando pessoa_id da foto é None, a chave "pessoa" no resultado
        deve ser None sem fazer query ao banco.
        """
        service = self._make_service()

        embedding = np.array([0.1] * 512)
        face_service = MagicMock()
        face_service.extrair_embedding.return_value = embedding

        foto = self._make_foto(foto_id=2, pessoa_id=None)

        service.repo.buscar_por_similaridade_facial = AsyncMock(return_value=[(foto, 0.7512)])

        # db.execute não deve ser chamado quando não há pessoa_ids
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        service.db.execute = AsyncMock(return_value=mock_result)

        results = await service.buscar_por_rosto(
            image_bytes=b"fake_image",
            face_service=face_service,
            top_k=5,
        )

        assert len(results) == 1
        assert results[0]["foto"] is foto
        assert results[0]["similaridade"] == 0.7512
        assert results[0]["pessoa"] is None
        # Sem pessoa_ids, db.execute não deve ser invocado
        service.db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_similaridade_arredondada(self):
        """Deve arredondar similaridade para 4 casas decimais.

        Args verificados: similaridade no resultado usa round(..., 4).
        """
        service = self._make_service()

        embedding = np.array([0.1] * 512)
        face_service = MagicMock()
        face_service.extrair_embedding.return_value = embedding

        foto = self._make_foto(foto_id=3, pessoa_id=None)
        service.repo.buscar_por_similaridade_facial = AsyncMock(return_value=[(foto, 0.987654321)])
        service.db.execute = AsyncMock()

        results = await service.buscar_por_rosto(
            image_bytes=b"fake_image",
            face_service=face_service,
        )

        assert results[0]["similaridade"] == 0.9877


class TestFotoComCompressaoStatus:
    """Testa que Foto possui campo compressao_status."""

    def test_foto_tem_campo_compressao_status(self):
        """Foto deve ter atributo compressao_status com default 'na'.

        Verifica existência da coluna no modelo e que o default de INSERT
        está configurado como 'na' (comportamento SQLAlchemy DeclarativeBase).
        """
        from sqlalchemy import inspect as sa_inspect

        from app.models.foto import Foto

        foto = Foto()
        assert hasattr(foto, "compressao_status")

        # Em DeclarativeBase sem MappedAsDataclass, defaults de coluna
        # são aplicados no INSERT, não no __init__. Verificamos a configuração.
        mapper = sa_inspect(Foto)
        col = mapper.columns["compressao_status"]
        assert col.default is not None
        assert col.default.arg == "na"
        assert col.server_default is not None
