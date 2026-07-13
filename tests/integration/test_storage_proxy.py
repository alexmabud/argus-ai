"""Testes de integração do proxy autenticado ``/storage/{path}``.

Valida streaming dos bytes do S3 (sem buffer em memória), propagação de
``ETag``/``If-None-Match`` para 304 nativo do S3, tratamento de erros
(404 para NoSuchKey, 502 para outros erros), enforcement de tenant
para midias de abordagem/PDFs de ocorrencia, e marca d'água nas imagens
(camada 2 do watermark rastreável).
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

    async def read(self) -> bytes:
        """Materializa todos os chunks em bytes.

        Compatível com ``download_with_meta``, que usa ``Body.read()``
        em vez de ``iter_chunks`` para acesso sem streaming.

        Returns:
            Concatenação de todos os chunks.
        """
        return b"".join(self._chunks)


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


def _get_obj_routing(return_value: dict) -> AsyncMock:
    """Cria mock de get_object que retorna NoSuchKey para keys wm/ e dados para outras.

    Necessário porque o proxy tenta o cache de watermark (prefixo wm/) antes
    de baixar o original: a primeira chamada deve falhar e a segunda retornar
    os dados esperados pelo teste.

    Args:
        return_value: Dict retornado para keys que não começam com ``wm/``.

    Returns:
        AsyncMock configurado com side_effect de roteamento por prefixo.
    """

    async def _side(**kwargs: object) -> dict:
        """Roteia get_object: wm/ → NoSuchKey; outros → dados do teste."""
        if str(kwargs.get("Key", "")).startswith("wm/"):
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return return_value

    return AsyncMock(side_effect=_side)


@pytest.mark.asyncio
async def test_storage_proxy_streama_chunks_do_s3(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """Proxy deve usar StreamingResponse e iter_chunks para conteúdo não-imagem (PDF)."""
    await _indexar_foto(db_session, "fotos/x.jpg")
    body = _FakeStreamingBody([b"hello ", b"world"])
    # Usa application/pdf: não-imagem preserva o path de streaming (sem marcação).
    fake_storage.get_object = _get_obj_routing(
        {
            "Body": body,
            "ContentType": "application/pdf",
            "ETag": '"abc"',
            "ContentLength": 11,
        }
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/x.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["etag"] == '"abc"'
    assert response.headers["cache-control"] == "private, max-age=3600"
    assert response.content == b"hello world"
    # Confirma que iter_chunks foi chamado (streaming, não read())
    assert body.iter_calls, "iter_chunks deveria ter sido chamado"


@pytest.mark.asyncio
async def test_storage_proxy_nao_repassa_if_none_match_ao_s3(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """O proxy NÃO repassa If-None-Match ao S3 e nunca devolve 304.

    Como o proxy pode transformar os bytes (marca d'água), o ETag do original
    não valida o conteúdo servido. Honrar a requisição condicional fazia o
    browser servir cópias antigas sem marca. Agora sempre busca e serve 200.
    """
    await _indexar_foto(db_session, "fotos/x.jpg")
    body = _FakeStreamingBody([b"x"])
    fake_storage.get_object = _get_obj_routing(
        {"Body": body, "ContentType": "application/pdf", "ETag": '"abc"'}
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/x.jpg",
        headers={**auth_headers, "If-None-Match": '"abc"'},
    )

    assert response.status_code == 200
    # Nenhuma chamada ao S3 deve carregar IfNoneMatch.
    for call in fake_storage.get_object.call_args_list:
        assert "IfNoneMatch" not in call.kwargs


@pytest.mark.asyncio
async def test_storage_proxy_retorna_404_para_nosuchkey(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """NoSuchKey do S3 deve virar 404 do proxy.

    A Foto é indexada para exercitar o mapeamento NoSuchKey→404 (achado do
    S3), não o default-deny de objeto órfão (achado #08) — comportamentos
    distintos que agora convergem no mesmo status code.
    """
    await _indexar_foto(db_session, "fotos/missing.jpg")
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
async def test_storage_proxy_objeto_orfao_retorna_404_sem_chamar_s3(
    client, auth_headers, fake_storage
):
    """Objeto sem Foto/Ocorrencia/avatar de Usuario correspondente é default-deny.

    Achado #08/2026-07-13: antes, qualquer chave sem linha indexada era
    servida sem checagem — só o `NoSuchKey` do S3 (achado de existência real
    no bucket) resultava em 404. Agora a ausência de registro já barra antes
    de tocar no S3.
    """
    fake_storage.get_object = AsyncMock()

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/nao-indexada.jpg",
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


async def _indexar_foto(db_session: AsyncSession, path: str) -> Foto:
    """Cria uma Foto mínima apontando para ``path`` (sem pessoa/abordagem).

    O proxy agora é default-deny para objetos sem linha indexada (achado
    #08/2026-07-13) — testes que só exercitam mecânica de streaming/cache/
    watermark (não autorização) precisam de uma Foto real para não colidir
    com o 404 de "objeto órfão".
    """
    foto = Foto(arquivo_url=f"/storage/{settings.S3_BUCKET}/{path}", data_hora=datetime.now())
    db_session.add(foto)
    await db_session.flush()
    return foto


@pytest.mark.asyncio
async def test_storage_proxy_midia_de_abordagem_e_global_mesmo_com_isolamento(
    client, auth_headers, fake_storage, db_session, usuario, guarnicao, bpm
):
    """Mídia de abordagem é GLOBAL mesmo com isolamento_abordagens ligado.

    Regra de negócio: a ficha da pessoa mostra fotos e GPS das abordagens de
    TODAS as equipes para qualquer usuário. O isolamento_abordagens atua apenas
    na LISTAGEM de relatórios/consultas (não revela QUEM fez), nunca na mídia —
    por isso o /storage serve a foto de outra equipe mesmo com o isolamento da
    equipe do usuário ligado. O watermark por matrícula preserva a rastreabilidade.
    """
    guarnicao.isolamento_abordagens = True
    await db_session.flush()

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

    body = _FakeStreamingBody([b"\x00"])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": body, "ContentType": "image/jpeg", "ETag": '"x"'}
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/midia_outra_abordagem.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_storage_proxy_libera_midia_de_abordagem_de_outra_equipe_sem_isolamento(
    client, auth_headers, fake_storage, db_session, usuario, bpm
):
    """Sem isolamento (padrão), mídia de abordagem de outra equipe também é global."""
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

    body = _FakeStreamingBody([b"\x00"])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": body, "ContentType": "image/jpeg", "ETag": '"x"'}
    )

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/midia_outra_abordagem.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 200


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
    fake_storage.upload = AsyncMock()

    response = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/minha_midia.jpg",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_storage_proxy_marca_imagem_inline(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """Imagem servida pelo proxy volta marcada (bytes != original)."""
    import io

    from PIL import Image

    await _indexar_foto(db_session, "fotos/uuid_x.jpg")
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (100, 100, 100)).save(buf, format="JPEG")
    original = buf.getvalue()

    body = _FakeStreamingBody([original])
    # cache miss (wm/ → NoSuchKey) + original retorna imagem real
    fake_storage.get_object = _get_obj_routing(
        {"Body": body, "ContentType": "image/jpeg", "ETag": '"img"'}
    )
    fake_storage.upload = AsyncMock()

    resp = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/uuid_x.jpg",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content != original  # marcado


@pytest.mark.asyncio
async def test_storage_proxy_marca_imagem_com_content_type_jpg_nao_padrao(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """Imagem com content-type não-padrão (image/jpg) também é marcada.

    Regressão: clientes (iOS, alguns browsers) enviam `image/jpg` em vez de
    `image/jpeg`. O upload gravava esse MIME verbatim e o proxy não marcava,
    deixando o original exibido sem marca d'água ao ampliar.
    """
    import io

    from PIL import Image

    await _indexar_foto(db_session, "fotos/uuid_jpg.jpg")
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (100, 100, 100)).save(buf, format="JPEG")
    original = buf.getvalue()

    body = _FakeStreamingBody([original])
    fake_storage.get_object = _get_obj_routing(
        {"Body": body, "ContentType": "image/jpg", "ETag": '"jpg"'}
    )
    fake_storage.upload = AsyncMock()

    resp = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/uuid_jpg.jpg",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content != original  # marcado apesar do content-type não-padrão


@pytest.mark.asyncio
async def test_storage_proxy_ignora_if_none_match_de_imagem_e_marca(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """Imagem com If-None-Match (cache antigo) NÃO recebe 304 — é remarcada.

    Regressão: thumbnails cacheados pelo browser antes do watermark guardavam
    o ETag do original. Ao revalidar, o proxy repassava o If-None-Match ao S3,
    que respondia 304, e o browser servia a cópia SEM marca para sempre. O proxy
    não pode honrar o ETag do original para conteúdo que ele transforma (marca).
    """
    import io

    from PIL import Image

    await _indexar_foto(db_session, "thumbs/x_thumb.jpg")
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), (100, 100, 100)).save(buf, format="JPEG")
    original = buf.getvalue()

    async def _side(**kwargs: object) -> dict:
        """wm/ → miss; com IfNoneMatch → 304 do S3; sem → imagem real."""
        key = str(kwargs.get("Key", ""))
        if key.startswith("wm/"):
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        if kwargs.get("IfNoneMatch"):
            raise ClientError(
                {"Error": {"Code": "304"}, "ResponseMetadata": {"HTTPStatusCode": 304}},
                "GetObject",
            )
        return {"Body": _FakeStreamingBody([original]), "ContentType": "image/jpeg", "ETag": '"o"'}

    fake_storage.get_object = AsyncMock(side_effect=_side)
    fake_storage.upload = AsyncMock()

    resp = await client.get(
        f"/storage/{settings.S3_BUCKET}/thumbs/x_thumb.jpg",
        headers={**auth_headers, "If-None-Match": '"o"'},
    )
    assert resp.status_code == 200  # não 304
    assert resp.content != original  # marcado


@pytest.mark.asyncio
async def test_storage_proxy_rejeita_prefixo_wm(client, auth_headers, fake_storage):
    """Path com prefixo wm/ (cache interno) é rejeitado com 404."""
    fake_storage.get_object = AsyncMock()

    resp = await client.get(
        f"/storage/{settings.S3_BUCKET}/wm/v1/abc/fotos/x.jpg",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    fake_storage.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_storage_proxy_cache_hit_retorna_sem_chamar_original(
    client, auth_headers, fake_storage, db_session: AsyncSession
):
    """No fast-path (cache hit no MinIO), o original não é baixado do S3.

    get_object deve ser chamado exatamente uma vez (para a chave wm/),
    e a resposta deve conter os bytes cacheados, não reprocessar a imagem.
    """
    import io

    from PIL import Image

    await _indexar_foto(db_session, "fotos/cached.jpg")
    pre_marked = io.BytesIO()
    Image.new("RGB", (200, 200), (10, 20, 30)).save(pre_marked, format="JPEG")
    pre_marked_bytes = pre_marked.getvalue()

    # get_object retorna bytes pré-marcados para qualquer key (simula cache hit).
    fake_body = _FakeStreamingBody([pre_marked_bytes])
    fake_storage.get_object = AsyncMock(
        return_value={"Body": fake_body, "ContentType": "image/jpeg"}
    )

    resp = await client.get(
        f"/storage/{settings.S3_BUCKET}/fotos/cached.jpg",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content == pre_marked_bytes
    # Exatamente uma chamada: a do cache wm/, não do original
    assert fake_storage.get_object.call_count == 1
