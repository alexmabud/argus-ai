"""Testes unitários do reporter diário (``monitoring/reporter/daily_report.py``).

Valida que falhas reais de consulta ao Prometheus (rede/HTTP/parse) não são
mascaradas como "sem dados" — nem no relatório enviado, nem no exit code do
processo (achado #28/2026-07-13).
"""

import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "monitoring" / "reporter" / "daily_report.py"

os.environ.setdefault("PROMETHEUS_URL", "http://prometheus.test:9090")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "fake-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "fake-chat-id")

_spec = importlib.util.spec_from_file_location("daily_report", _SCRIPT)
daily_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daily_report)


def _resp_vazia(*_args, **_kwargs) -> MagicMock:
    """Resposta HTTP 200 do Prometheus sem nenhuma série (comportamento normal)."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"data": {"result": []}}
    return resp


def _resp_telegram_ok(*_args, **_kwargs) -> MagicMock:
    """Resposta HTTP 200 do Telegram (envio bem-sucedido)."""
    resp = MagicMock()
    resp.ok = True
    return resp


class TestQueryRangeMax:
    """Testes de query_range_max() isolada."""

    def test_erro_http_e_registrado_nao_apenas_retorna_none(self, monkeypatch):
        """Erro de rede/HTTP em query_range_max fica em _query_errors, não só vira None.

        Antes, query_range_max engolia QUALQUER exceção em silêncio — o
        chamador via None, indistinguível de "sem dados no período".
        """
        daily_report._query_errors.clear()

        def _raise(*_a, **_k):
            raise ConnectionError("Prometheus indisponível")

        monkeypatch.setattr(daily_report.requests, "get", _raise)

        resultado = daily_report.query_range_max("up")

        assert resultado is None
        assert len(daily_report._query_errors) == 1

    def test_resposta_sem_dados_nao_e_erro(self, monkeypatch):
        """Query bem-sucedida mas sem séries não conta como erro (é "sem dados" real)."""
        daily_report._query_errors.clear()
        monkeypatch.setattr(daily_report.requests, "get", _resp_vazia)

        resultado = daily_report.query_range_max("up")

        assert resultado is None
        assert daily_report._query_errors == []


class TestMain:
    """Testes de main() fim a fim (com Prometheus/Telegram mockados)."""

    def _mock_ok(self, monkeypatch):
        """Mocka Prometheus (sempre sem dados, sem erro) e Telegram (sucesso)."""
        monkeypatch.setattr(daily_report.requests, "get", _resp_vazia)
        monkeypatch.setattr(daily_report.requests, "post", _resp_telegram_ok)

    def test_main_sem_erros_de_query_nao_sai_com_status_de_falha(self, monkeypatch):
        """Sem nenhuma falha de consulta, main() não levanta SystemExit."""
        self._mock_ok(monkeypatch)

        daily_report.main()  # não deve levantar SystemExit

    def test_main_com_erro_de_query_sai_com_codigo_2(self, monkeypatch):
        """Se alguma consulta falhar de verdade, main() sai com código 2 (achado #28).

        O relatório ainda deve ser enviado (dado parcial é melhor que
        nenhum) — só o exit code sinaliza o run como degradado.
        """
        call_count = {"n": 0}

        def _get_com_falha_intermitente(url, **kwargs):
            call_count["n"] += 1
            # A primeira chamada de range (CPU) falha; as demais respondem vazio.
            if "query_range" in url and call_count["n"] <= 1:
                raise ConnectionError("Prometheus indisponível")
            return _resp_vazia()

        monkeypatch.setattr(daily_report.requests, "get", _get_com_falha_intermitente)
        sent = {}

        def _post_captura(url, json=None, **kwargs):
            sent["json"] = json
            return _resp_telegram_ok()

        monkeypatch.setattr(daily_report.requests, "post", _post_captura)

        with pytest.raises(SystemExit) as exc_info:
            daily_report.main()

        assert exc_info.value.code == 2
        # A mensagem ainda foi enviada, com o aviso de falha no topo.
        assert "consulta(s) ao Prometheus falharam" in sent["json"]["text"]

    def test_main_reseta_erros_entre_execucoes(self, monkeypatch):
        """_query_errors de uma execução anterior não vaza para a próxima."""

        # Primeira execução: força um erro.
        def _get_com_erro(url, **kwargs):
            raise ConnectionError("falha")

        monkeypatch.setattr(daily_report.requests, "get", _get_com_erro)
        monkeypatch.setattr(daily_report.requests, "post", _resp_telegram_ok)
        with pytest.raises(SystemExit):
            daily_report.main()
        assert daily_report._query_errors  # população confirmada

        # Segunda execução: tudo ok — não deve herdar os erros da primeira.
        self._mock_ok(monkeypatch)
        daily_report.main()  # não deve levantar SystemExit
        assert daily_report._query_errors == []
