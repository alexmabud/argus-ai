"""Testes de integração do proxy autenticado ``/storage/{path}``.

Valida streaming dos bytes do S3 (sem buffer em memória), propagação de
``ETag``/``If-None-Match`` para 304 nativo do S3, tratamento de erros
(404 para NoSuchKey, 502 para outros erros) e enforcement de tenant
para midias de abordagem/PDFs de ocorrencia.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bpm import Bpm
from app.models.foto import Foto
from app.models.guarnicao import Guarnicao
from app.models.ocorrencia import Ocorrencia
from app.services import storage_service as ss_module


class _FakeStreamingBody:
    """Stub do StreamingBody do aioboto3 com ``iter_chunks`` async.

    Devolve os chunks programados via construtor — usado para verificar
    que o proxy delega via ``async for`` sem materializar o arquivo.
    """

    def __init__(self, chunks: list[bytes]) -> None:
        """Inicializa o stub com a lista de chunks a entregar.

        Args:
            chunks: Lista de bytes que serão emitidos em sequência.
        """
        self._chunks = chunks
        self.iter_calls: list[int] = []

    def iter_chunks(self, chunk_size: int):
        """Retorna um async iterator dos chunks programados.

        Args:
            chunk_size: Tamanho do chunk solicitado pelo caller
                (gravado para inspeção em ``iter_calls``).

        Returns:
            Async generator que emite cada chunk em ordem.
        """
        self.iter_calls.append(chunk_size)

        async def _gen():
            for c in self._chunks:
                yield c

        return _gen()


@pytest.fixture(autouse=True)
def _reset_storage_singleton():
    """Reseta o singleton entre testes para isolar mocks."""
    ss_module.StorageService._instance = None
    yield
    ss_module.StorageService._instance = None


@pytest.fixture
async def fake_storage(monkeypatch):
    """Substitui o cliente S3 do singleton por um mock controlável.

    O ``AsyncClient`` com ``ASGITransport`` dos testes não dispara o
    lifespan da aplicação, então o ``startup()`` do singleton é
    executado manualmente aqui (já com o monkeypatch na ``Session``)
    para que o handler encontre o cliente pronto.

    Args:
        monkeypatch: Fixture pytest para patch temporário.

    Yields:
        Mock do cliente S3 (com ``get_object`` ``AsyncMock``).
    """
    fake_client = MagicMock()

    async def fake_aenter(self):
        return fake_client

    async def fake_aexit(self, *a):
        return None

    monkeypatch.setattr(
        ss_module.aioboto3.Session,
        "client",
        lambda self, *a, **kw: type(
            "CM", (), {"__aenter__": fake_aenter, "__aexit__": fake_aexit}
        )(),
    )
    service = ss_module.StorageService.get()
    await service.startup()
    try:
        yield fake_client
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_storage_proxy_streama_chunks_do_s3(client, auth_headers, fake_storage):
    """Proxy deve usar StreamingResponse e iter_chunks (não baixar tudo)."""
    body = _FakeStreamingBody([b"hello ", b"world"])
    fake_storage.get_object = AsyncMock(
        return_value={
            "Body": body,
            "ContentType": "image/jpeg",
            "ETag": '"abc"',
            "ContentLength": 11,
        }
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/x.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.headers["etag"] == '"abc"'
    assert response.headers["cache-control"] == "private, max-age=3600"
    assert response.content == b"hello world"
    # Confirma que iter_chunks foi chamado (streaming, não read())
    assert body.iter_calls, "iter_chunks deveria ter sido chamado"


@pytest.mark.asyncio
async def test_storage_proxy_repassa_if_none_match_para_s3(client, auth_headers, fake_storage):
    """If-None-Match do cliente deve virar IfNoneMatch no get_object."""
    body = _FakeStreamingBody([b"x"])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": body, "ContentType": "image/jpeg", "ETag": '"abc"'}
    )

    await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/x.jpg",
        headers={**auth_headers, "If-None-Match": '"abc"'},
    )

    kwargs = fake_storage.get_object.call_args.kwargs
    assert kwargs.get("IfNoneMatch") == '"abc"'


@pytest.mark.asyncio
async def test_storage_proxy_retorna_304_quando_s3_responde_not_modified(
    client, auth_headers, fake_storage
):
    """Quando S3 lança 304/NotModified, proxy devolve 304 sem body."""
    error = ClientError(
        {
            "Error": {"Code": "304", "Message": "Not Modified"},
            "ResponseMetadata": {"HTTPStatusCode": 304},
        },
        "GetObject",
    )
    fake_storage.get_object = AsyncMock(side_effect=error)

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/x.jpg",
        headers={**auth_headers, "If-None-Match": '"abc"'},
    )

    assert response.status_code == 304
    assert response.content == b""
    assert response.headers.get("etag") == '"abc"'


@pytest.mark.asyncio
async def test_storage_proxy_retorna_404_para_nosuchkey(client, auth_headers, fake_storage):
    """NoSuchKey do S3 deve virar 404 do proxy."""
    error = ClientError(
        {
            "Error": {"Code": "NoSuchKey", "Message": "Not found"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        },
        "GetObject",
    )
    fake_storage.get_object = AsyncMock(side_effect=error)

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/missing.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_storage_proxy_rejeita_bucket_diferente(client, auth_headers, fake_storage):
    """Path apontando para outro bucket deve retornar 404 sem chamar S3."""
    fake_storage.get_object = AsyncMock()

    response = await client.get(
        "/storage/bucket-malicioso/fotos/x.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 404
    fake_storage.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_storage_proxy_sem_autenticacao_retorna_401(client, fake_storage):
    """Sem JWT, o proxy não pode liberar arquivos privados."""
    fake_storage.get_object = AsyncMock()

    response = await client.get(f"/storage/{settings.S3_BUCKET}/fotos/x.jpg")

    assert response.status_code == 401
    fake_storage.get_object.assert_not_called()


async def _outra_equipe(db_session: AsyncSession, bpm: Bpm) -> Guarnicao:
    """Cria uma guarnicao distinta da fixture padrao para isolar tenant."""
    g = Guarnicao(nome="Outra Equipe", bpm_id=bpm.id, codigo="OUTRA-EQUIPE")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.mark.asyncio
async def test_storage_proxy_bloqueia_midia_de_abordagem_de_outra_equipe(
    client, auth_headers, fake_storage, db_session, usuario, bpm
):
    """Foto vinculada a abordagem (pessoa_id=None) de outra equipe deve dar 403.

    Modelo de produto: fotos de pessoa = globais; demais midias operacionais
    (RAP, foto direta de abordagem) respeitam isolamento BPM/equipe.
    """
    outra = await _outra_equipe(db_session, bpm)
    foto = Foto(
        arquivo_url=f"/storage/{settings.S3_BUCKET}/fotos/midia_outra_abordagem.jpg",
        tipo="abordagem",
        data_hora=datetime.now(),
        pessoa_id=None,
        guarnicao_id=outra.id,
    )
    db_session.add(foto)
    await db_session.flush()

    fake_storage.get_object = AsyncMock()

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/midia_outra_abordagem.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 403
    fake_storage.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_storage_proxy_libera_foto_de_pessoa_de_outra_equipe(
    client, auth_headers, fake_storage, db_session, usuario, bpm
):
    """Foto vinculada a pessoa (pessoa_id != None) eh global mesmo cross-team.

    Modelo de produto: BNMP/passagens compartilhadas. Bloquear este caso
    quebraria fluxo operacional.
    """
    from app.models.pessoa import Pessoa

    outra = await _outra_equipe(db_session, bpm)
    pessoa = Pessoa(nome="Cidadao X", guarnicao_id=outra.id)
    db_session.add(pessoa)
    await db_session.flush()
    foto = Foto(
        arquivo_url=f"/storage/{settings.S3_BUCKET}/fotos/pessoa_global.jpg",
        tipo="rosto",
        data_hora=datetime.now(),
        pessoa_id=pessoa.id,
        guarnicao_id=outra.id,
    )
    db_session.add(foto)
    await db_session.flush()

    body = _FakeStreamingBody([b"\x00"])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": body, "ContentType": "image/jpeg", "ETag": '"x"'}
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/pessoa_global.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_storage_proxy_bloqueia_pdf_de_ocorrencia_de_outra_equipe(
    client, auth_headers, fake_storage, db_session, usuario, bpm
):
    """PDF de ocorrencia (RAP) de outra equipe deve dar 403.

    Mesma logica das midias de abordagem: documento operacional eh tenant-scoped.
    """
    from datetime import date

    outra = await _outra_equipe(db_session, bpm)
    ocorrencia = Ocorrencia(
        numero_ocorrencia="2026.00001/OUTRA",
        arquivo_pdf_url=f"/storage/{settings.S3_BUCKET}/pdfs/rap_outra.pdf",
        data_ocorrencia=date.today(),
        usuario_id=usuario.id,
        guarnicao_id=outra.id,
    )
    db_session.add(ocorrencia)
    await db_session.flush()

    fake_storage.get_object = AsyncMock()

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/pdfs/rap_outra.pdf",
        headers=auth_headers,
    )
    assert response.status_code == 403
    fake_storage.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_storage_proxy_libera_midia_de_abordagem_propria(
    client, auth_headers, fake_storage, db_session, usuario
):
    """Midia de abordagem da propria equipe deve passar normalmente."""
    foto = Foto(
        arquivo_url=f"/storage/{settings.S3_BUCKET}/fotos/minha_midia.jpg",
        tipo="abordagem",
        data_hora=datetime.now(),
        pessoa_id=None,
        guarnicao_id=usuario.guarnicao_id,
    )
    db_session.add(foto)
    await db_session.flush()

    body = _FakeStreamingBody([b"\x00"])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": body, "ContentType": "image/jpeg", "ETag": '"x"'}
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/minha_midia.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 200
