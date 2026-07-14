"""Testes unitários para FotoService.

Valida enriquecimento de resultados com dados da pessoa vinculada,
enforcement da quota de fotos por abordagem e soft delete de fotos.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, NaoEncontradoError, QuotaExcedidaError
from app.core.security import hash_senha
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.services.foto_service import QUOTA_FOTOS_POR_ABORDAGEM, FotoService


def _make_service_para_quota():
    db = AsyncMock()
    with patch("app.services.foto_service.StorageService"):
        service = FotoService(db)
    service.repo = AsyncMock()
    service.audit = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_upload_foto_rejeita_quando_quota_atingida():
    """Upload alem de QUOTA_FOTOS_POR_ABORDAGEM deve dar QuotaExcedidaError.

    Sem essa checagem, conta comprometida grava 6 GB/h no R2
    (10 fotos/min x 10 MB).
    """
    service = _make_service_para_quota()
    service.repo.count_by_abordagem = AsyncMock(return_value=QUOTA_FOTOS_POR_ABORDAGEM)
    with pytest.raises(QuotaExcedidaError):
        await service.upload_foto(
            file_bytes=b"\xff\xd8\xff\xe0",
            filename="ok.jpg",
            content_type="image/jpeg",
            pessoa_id=None,
            abordagem_id=1,
            veiculo_id=None,
            tipo="abordagem",
            latitude=None,
            longitude=None,
            user_id=1,
        )


@pytest.mark.asyncio
async def test_upload_foto_sem_abordagem_nao_checa_quota():
    """Uploads sem abordagem_id (ex: foto de pessoa) nao sao limitados por quota."""
    service = _make_service_para_quota()
    service.repo.count_by_abordagem = AsyncMock(return_value=999_999)
    service.storage.generate_key = MagicMock(return_value="fotos/x.jpg")
    service.storage.upload = AsyncMock(return_value="/storage/argus/fotos/x.jpg")
    service.repo.create = AsyncMock(return_value=MagicMock(id=1))
    # Nao deve levantar QuotaExcedidaError mesmo com count enorme:
    # quando abordagem_id eh None nao checamos.
    try:
        await service.upload_foto(
            file_bytes=b"\xff\xd8\xff\xe0",
            filename="ok.jpg",
            content_type="image/jpeg",
            pessoa_id=42,
            abordagem_id=None,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=1,
        )
    except QuotaExcedidaError:
        pytest.fail("Quota nao deveria aplicar quando abordagem_id eh None")


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

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_usa_threshold_de_settings_por_padrao(self):
        """Sem threshold explícito, repassa settings.FACE_SIMILARITY_THRESHOLD ao repo.

        Achado #26/2026-07-13: antes o service não passava threshold nenhum
        para o repositório, que sempre aplicava seu próprio default hardcoded
        (0.6) — a configuração de settings nunca chegava a valer, mesmo que
        alterada via env.
        """
        from app.config import settings

        service = self._make_service()
        embedding = np.array([0.1] * 512)
        face_service = MagicMock()
        face_service.extrair_embedding.return_value = embedding
        service.repo.buscar_por_similaridade_facial = AsyncMock(return_value=[])

        await service.buscar_por_rosto(image_bytes=b"fake_image", face_service=face_service)

        service.repo.buscar_por_similaridade_facial.assert_awaited_once()
        kwargs = service.repo.buscar_por_similaridade_facial.call_args.kwargs
        assert kwargs["threshold"] == settings.FACE_SIMILARITY_THRESHOLD

    @pytest.mark.asyncio
    async def test_buscar_por_rosto_threshold_explicito_sobrepoe_settings(self):
        """threshold explícito tem prioridade sobre settings.FACE_SIMILARITY_THRESHOLD."""
        service = self._make_service()
        embedding = np.array([0.1] * 512)
        face_service = MagicMock()
        face_service.extrair_embedding.return_value = embedding
        service.repo.buscar_por_similaridade_facial = AsyncMock(return_value=[])

        await service.buscar_por_rosto(
            image_bytes=b"fake_image", face_service=face_service, threshold=0.9
        )

        kwargs = service.repo.buscar_por_similaridade_facial.call_args.kwargs
        assert kwargs["threshold"] == 0.9


class TestUploadFotoThumbnail:
    """Testes para geração de thumbnail no fluxo de upload_foto."""

    def _make_service_para_upload(self, upload_urls: list[str]):
        """Cria FotoService com storage mockado retornando URLs em sequência.

        Mocka ``StorageService.get()`` para devolver um stub cujo ``upload``
        retorna as URLs informadas na ordem das chamadas (foto, thumb).

        Args:
            upload_urls: URLs sequenciais a retornar em cada chamada ``upload``.

        Returns:
            Tupla (service, storage_mock) com mocks prontos para uso.
        """
        from app.services.foto_service import FotoService

        db = AsyncMock()
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(
            side_effect=lambda prefix, filename: f"{prefix}/abc_{filename}"
        )
        storage_mock.upload = AsyncMock(side_effect=list(upload_urls))

        with patch(
            "app.services.foto_service.StorageService.get",
            return_value=storage_mock,
        ):
            service = FotoService(db)
        service.repo = AsyncMock()
        service.repo.count_by_abordagem = AsyncMock(return_value=0)
        service.audit = AsyncMock()
        return service, storage_mock

    @pytest.mark.asyncio
    async def test_upload_foto_gera_thumbnail(self):
        """Upload de imagem deve gerar e salvar thumbnail_url.

        Quando ``content_type`` começa com ``image/``, o serviço deve gerar
        thumb via ``gerar_thumbnail`` e fazer upload separado, salvando a URL
        resultante no campo ``thumbnail_url`` da Foto.
        """
        import io

        from PIL import Image

        img = Image.new("RGB", (1200, 800), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        service, storage_mock = self._make_service_para_upload(
            upload_urls=[
                "/storage/argus/fotos/abc_abordagem.jpg",
                "/storage/argus/thumbs/abc_abordagem_thumb.jpg",
            ]
        )

        foto = await service.upload_foto(
            file_bytes=img_bytes,
            filename="abordagem.jpg",
            content_type="image/jpeg",
            pessoa_id=None,
            abordagem_id=1,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=1,
        )

        assert foto.thumbnail_url == "/storage/argus/thumbs/abc_abordagem_thumb.jpg"
        assert foto.arquivo_url == "/storage/argus/fotos/abc_abordagem.jpg"
        assert foto.thumbnail_url != foto.arquivo_url
        # Storage.upload deve ter sido chamado duas vezes: foto original + thumb
        assert storage_mock.upload.await_count == 2

    @pytest.mark.asyncio
    async def test_upload_pdf_nao_gera_thumbnail(self):
        """PDFs e vídeos não devem tentar gerar thumb.

        Para ``content_type`` que não começa com ``image/``, o serviço deve
        pular a geração de thumb. ``thumbnail_url`` permanece ``None`` e o
        storage.upload é chamado apenas uma vez.
        """
        service, storage_mock = self._make_service_para_upload(
            upload_urls=["/storage/argus/fotos/abc_auto.pdf"]
        )
        pdf_bytes = b"%PDF-1.4\n%fake"

        foto = await service.upload_foto(
            file_bytes=pdf_bytes,
            filename="auto.pdf",
            content_type="application/pdf",
            pessoa_id=None,
            abordagem_id=1,
            veiculo_id=None,
            tipo="midia_abordagem",
            latitude=None,
            longitude=None,
            user_id=1,
            max_size=200 * 1024 * 1024,
        )

        assert foto.thumbnail_url is None
        assert foto.arquivo_url == "/storage/argus/fotos/abc_auto.pdf"
        # Apenas o upload original — sem chamada extra para thumb
        assert storage_mock.upload.await_count == 1

    @pytest.mark.asyncio
    async def test_upload_imagem_thumb_falha_nao_quebra_upload(self):
        """Falha ao gerar thumb deve apenas logar — upload da foto continua.

        Garante que a geração de thumb é tratada como otimização: se
        ``gerar_thumbnail`` ou o upload do thumb falham, a Foto ainda é
        criada com ``thumbnail_url=None``.
        """
        service, storage_mock = self._make_service_para_upload(
            upload_urls=["/storage/argus/fotos/abc_foto.jpg"]
        )

        # Bytes inválidos — PIL falha ao abrir
        bytes_invalidos = b"not-a-real-image"

        foto = await service.upload_foto(
            file_bytes=bytes_invalidos,
            filename="foto.jpg",
            content_type="image/jpeg",
            pessoa_id=None,
            abordagem_id=1,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=1,
        )

        assert foto.thumbnail_url is None
        assert foto.arquivo_url == "/storage/argus/fotos/abc_foto.jpg"
        # Só o upload original — geração falhou antes do segundo upload
        assert storage_mock.upload.await_count == 1


class TestDesativarFoto:
    """Testes para FotoService.desativar (soft delete)."""

    async def test_desativa_foto_com_sucesso(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Deve marcar a foto como inativa (ativo=False) preservando o registro.

        Apagar foto é restrito a administradores, por isso ``usuario`` precisa
        do flag ``is_admin`` para que a desativação seja permitida.
        """
        usuario.is_admin = True

        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")
        storage_mock.upload = AsyncMock(return_value="/storage/argus/fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="teste.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="evidencia",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert foto.ativo is True

        desativada = await service.desativar(foto.id, usuario)
        assert desativada.ativo is False

    async def test_desativar_foto_por_usuario_nao_admin_levanta_acesso_negado(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Deve levantar AcessoNegadoError quando quem apaga não é admin.

        Mesmo sendo da mesma guarnição da foto (e ainda que tenha sido quem
        fez o upload), um usuário sem ``is_admin`` não pode apagar fotos.
        """
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")
        storage_mock.upload = AsyncMock(return_value="/storage/argus/fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="teste.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="evidencia",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )

        with pytest.raises(AcessoNegadoError):
            await service.desativar(foto.id, usuario)

    async def test_desativar_foto_de_outra_guarnicao_levanta_acesso_negado(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Deve levantar AcessoNegadoError ao desativar foto de outra guarnição.

        A foto pertence à guarnição de ``usuario`` (tenant A). Um segundo
        usuário não-admin criado em outra guarnição (tenant B) não pode
        desativá-la — bloqueado já pelo gate de admin, antes mesmo de
        chegar na checagem de tenant.
        """
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")
        storage_mock.upload = AsyncMock(return_value="/storage/argus/fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="teste.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="evidencia",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )

        # Cria segunda guarnição (tenant B) e usuário nela
        bpm_b = Bpm(nome="5o BPM Fotos")
        db_session.add(bpm_b)
        await db_session.flush()
        guarnicao_b = Guarnicao(nome="5a Cia - GU 02", bpm_id=bpm_b.id, codigo="5BPM-5CIA-GU02")
        db_session.add(guarnicao_b)
        await db_session.flush()
        usuario_b = Usuario(
            nome="Agente Outro Tenant",
            matricula="OTHER001",
            senha_hash=hash_senha("senha123"),
            guarnicao_id=guarnicao_b.id,
        )
        db_session.add(usuario_b)
        await db_session.flush()

        with pytest.raises(AcessoNegadoError):
            await service.desativar(foto.id, usuario_b)

    async def test_desativar_foto_inexistente_levanta_erro(
        self, db_session: AsyncSession, usuario: Usuario
    ):
        """Deve levantar NaoEncontradoError quando a foto não existe."""
        usuario.is_admin = True
        service = FotoService(db_session)
        with pytest.raises(NaoEncontradoError):
            await service.desativar(99999, usuario)

    async def test_desativar_zera_embedding_e_apaga_original_e_thumbnail_do_storage(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Desativar exerce o direito de eliminação (LGPD) na hora, não só em 5 anos.

        Regressão do achado #02/2026-07-13: soft delete deixava o embedding
        buscável e o blob no storage indefinidamente (só a varredura de
        retenção de ``anonimizar_dados.py`` limpava, e só se a Pessoa também
        fosse soft-deleted).
        """
        usuario.is_admin = True

        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")
        storage_mock.upload = AsyncMock(return_value="/storage/argus-fotos/fotos/teste.jpg")
        storage_mock.delete = AsyncMock()

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="teste.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        foto.embedding_face = np.random.rand(512).tolist()
        foto.thumbnail_url = "/storage/argus-fotos/fotos/teste_thumb.jpg"
        await db_session.flush()

        desativada = await service.desativar(foto.id, usuario)

        assert desativada.embedding_face is None
        storage_mock.delete.assert_any_call("fotos/teste.jpg")
        storage_mock.delete.assert_any_call("fotos/teste_thumb.jpg")

    async def test_desativar_nao_quebra_se_storage_delete_falhar(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Falha ao apagar do storage não deve impedir o soft delete (best-effort)."""
        usuario.is_admin = True

        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")
        storage_mock.upload = AsyncMock(return_value="/storage/argus-fotos/fotos/teste.jpg")
        storage_mock.delete = AsyncMock(side_effect=RuntimeError("S3 indisponível"))

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="teste.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )

        desativada = await service.desativar(foto.id, usuario)
        assert desativada.ativo is False


class TestRecomputeFotoPrincipal:
    """Testes para recomputo de Pessoa.foto_principal_url ao desativar/enviar fotos.

    Cobre o bug em que a foto de perfil ficava travada numa foto errada
    (ex: foto de carro enviada por engano como tipo="rosto") mesmo depois
    dela ser desativada, porque o campo era gravado direto no upload e
    nunca recalculado no soft-delete.
    """

    async def _upload_rosto(
        self, service: FotoService, pessoa: Pessoa, usuario: Usuario, guarnicao: Guarnicao, url: str
    ):
        """Faz upload de uma foto tipo=rosto com uma arquivo_url determinística."""
        service.storage.upload = AsyncMock(return_value=url)
        return await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="rosto.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="rosto",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )

    async def test_desativar_foto_de_perfil_recua_para_rosto_ativa_mais_recente(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Ao desativar a foto de rosto que é o perfil, deve recuar para a próxima mais recente."""
        usuario.is_admin = True
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto_antiga = await self._upload_rosto(
            service, pessoa, usuario, guarnicao, "/storage/argus/fotos/antiga.jpg"
        )
        foto_recente = await self._upload_rosto(
            service, pessoa, usuario, guarnicao, "/storage/argus/fotos/recente.jpg"
        )
        assert pessoa.foto_principal_url == foto_recente.arquivo_url

        await service.desativar(foto_recente.id, usuario)

        assert pessoa.foto_principal_url == foto_antiga.arquivo_url

    async def test_desativar_unica_foto_rosto_zera_perfil(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Ao desativar a única foto de rosto ativa, o perfil deve ficar vazio."""
        usuario.is_admin = True
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto = await self._upload_rosto(
            service, pessoa, usuario, guarnicao, "/storage/argus/fotos/unica.jpg"
        )
        assert pessoa.foto_principal_url == foto.arquivo_url

        await service.desativar(foto.id, usuario)

        assert pessoa.foto_principal_url is None
        assert pessoa.foto_principal_thumb_url is None

    async def test_desativar_foto_nao_rosto_nao_altera_perfil(
        self, db_session: AsyncSession, guarnicao: Guarnicao, pessoa: Pessoa, usuario: Usuario
    ):
        """Desativar uma foto que não é rosto (ex: carro) não deve mexer no perfil."""
        usuario.is_admin = True
        storage_mock = MagicMock()
        storage_mock.generate_key = MagicMock(return_value="fotos/teste.jpg")

        with patch("app.services.foto_service.StorageService.get", return_value=storage_mock):
            service = FotoService(db_session)

        foto_rosto = await self._upload_rosto(
            service, pessoa, usuario, guarnicao, "/storage/argus/fotos/rosto.jpg"
        )
        service.storage.upload = AsyncMock(return_value="/storage/argus/fotos/carro.jpg")
        foto_veiculo = await service.upload_foto(
            file_bytes=b"fake-image-bytes",
            filename="carro.jpg",
            content_type="image/jpeg",
            pessoa_id=pessoa.id,
            abordagem_id=None,
            veiculo_id=None,
            tipo="veiculo",
            latitude=None,
            longitude=None,
            user_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        assert pessoa.foto_principal_url == foto_rosto.arquivo_url

        await service.desativar(foto_veiculo.id, usuario)

        assert pessoa.foto_principal_url == foto_rosto.arquivo_url


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
