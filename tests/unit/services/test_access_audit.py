"""Testes da camada 3 do watermark rastreável: auditoria de acesso."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import BackgroundTasks

from app.services import access_audit as mod
from app.services.access_audit import log_download, log_view


async def _run_tasks(bt: BackgroundTasks) -> None:
    """Executa todas as BackgroundTasks enfileiradas.

    Args:
        bt: Instância de BackgroundTasks com tarefas a executar.
    """
    for task in bt.tasks:
        await task()


async def test_log_download_sempre_agenda_audit(monkeypatch):
    """log_download agenda _audit_background independente de de-dupe.

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_audit = AsyncMock()
    monkeypatch.setattr(mod, "_audit_background", mock_audit)

    bt = BackgroundTasks()
    log_download(
        bt,
        usuario_id=1,
        matricula="GM-1",
        asset_key="fotos/x.jpg",
        foto_id=42,
        ip_address="10.0.0.1",
        user_agent="TestAgent/1",
    )
    await _run_tasks(bt)

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["acao"] == "DOWNLOAD_MIDIA"
    assert kwargs["recurso_id"] == 42
    assert "fotos/x.jpg" in kwargs["detalhes"]["asset_key"]


async def test_log_view_primeira_vez_loga(monkeypatch):
    """log_view registra audit quando de-dupe libera (primeira vez).

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_audit = AsyncMock()
    mock_dedup = AsyncMock(return_value=True)
    monkeypatch.setattr(mod, "_audit_background", mock_audit)
    monkeypatch.setattr(mod, "_dedup_view", mock_dedup)

    bt = BackgroundTasks()
    log_view(bt, usuario_id=1, matricula="GM-1", asset_key="fotos/x.jpg", foto_id=10)
    await _run_tasks(bt)

    mock_dedup.assert_awaited_once_with("GM-1", "fotos/x.jpg")
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["acao"] == "VIEW_MIDIA"


async def test_log_view_dedup_suprime_segundo_log(monkeypatch):
    """log_view não loga quando de-dupe retorna False (vista recente).

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_audit = AsyncMock()
    mock_dedup = AsyncMock(return_value=False)
    monkeypatch.setattr(mod, "_audit_background", mock_audit)
    monkeypatch.setattr(mod, "_dedup_view", mock_dedup)

    bt = BackgroundTasks()
    log_view(bt, usuario_id=1, matricula="GM-1", asset_key="fotos/x.jpg")
    await _run_tasks(bt)

    mock_audit.assert_not_awaited()


async def test_log_view_redis_indisponivel_loga_mesmo_assim(monkeypatch):
    """Se Redis cair, log_view loga mesmo assim (fail-open).

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_audit = AsyncMock()
    monkeypatch.setattr(mod, "_audit_background", mock_audit)
    monkeypatch.setattr(mod, "_redis_client", None)

    def _redis_broken():
        """Stub que simula Redis indisponível."""
        raise ConnectionError("Redis down")

    monkeypatch.setattr(mod, "_get_redis_client", _redis_broken)

    bt = BackgroundTasks()
    log_view(bt, usuario_id=1, matricula="GM-1", asset_key="fotos/x.jpg")
    await _run_tasks(bt)

    # fail-open: Redis indisponível não deve suprimir o log
    mock_audit.assert_awaited_once()


async def test_log_view_recurso_customizado_propaga(monkeypatch):
    """log_view propaga recurso!="foto" (ex.: "ocorrencia") até _audit_background.

    Achado #25/2026-07-13: antes recurso era sempre hardcoded "foto" em
    _audit_background, mesmo para PDF de Ocorrencia servido via /storage.

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_audit = AsyncMock()
    mock_dedup = AsyncMock(return_value=True)
    monkeypatch.setattr(mod, "_audit_background", mock_audit)
    monkeypatch.setattr(mod, "_dedup_view", mock_dedup)

    bt = BackgroundTasks()
    log_view(
        bt,
        usuario_id=1,
        matricula="GM-1",
        asset_key="pdfs/bo.pdf",
        foto_id=99,
        recurso="ocorrencia",
    )
    await _run_tasks(bt)

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["recurso"] == "ocorrencia"
    assert kwargs["recurso_id"] == 99


async def test_audit_background_abre_sessao_propria(monkeypatch):
    """_audit_background abre AsyncSessionLocal própria (não usa sessão do request).

    Args:
        monkeypatch: Fixture pytest para patch temporário.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_audit_svc = MagicMock()
    mock_audit_svc.log = AsyncMock()

    captured_sessions = []

    async def _fake_session_ctx():
        """Contexto de sessão falsa."""
        captured_sessions.append(mock_db)
        return mock_db

    # Simula `async with AsyncSessionLocal() as db:`
    fake_factory = MagicMock()
    fake_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    fake_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(mod, "AsyncSessionLocal", fake_factory)

    # Evita instanciar AuditService real
    monkeypatch.setattr(mod, "AuditService", lambda db: mock_audit_svc)

    await mod._audit_background(
        usuario_id=1,
        acao="DOWNLOAD_MIDIA",
        recurso_id=42,
        detalhes={"asset_key": "fotos/x.jpg"},
        ip_address="10.0.0.1",
        user_agent="test",
    )

    fake_factory.assert_called_once()  # nova sessão aberta
    mock_audit_svc.log.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
