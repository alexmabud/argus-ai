"""Relatório diário do Argus AI para o Telegram.

Roda via crond todo dia às 8h (horário de Brasília).
Consulta o Prometheus e envia resumo do dia anterior.
"""

import math
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

PROMETHEUS_URL = os.environ["PROMETHEUS_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DOMAIN = os.environ.get("DOMAIN", "arguseye.duckdns.org")

BRT = timezone(timedelta(hours=-3))


def query(promql: str) -> float | None:
    """Consulta um valor escalar no Prometheus.

    Args:
        promql: Expressão PromQL a ser consultada.

    Returns:
        Valor float do primeiro resultado, ou None se não houver dados.
    """
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=10,
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
        return None
    except Exception:
        return None


def query_range_max(promql: str, hours: int = 24) -> float | None:
    """Retorna o valor máximo de uma métrica nas últimas N horas.

    Args:
        promql: Expressão PromQL a ser consultada.
        hours: Janela de tempo em horas (padrão: 24h).

    Returns:
        Valor máximo float encontrado no período, ou None se sem dados.
    """
    end = datetime.now(tz=BRT)
    start = end - timedelta(hours=hours)
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": promql,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": "60s",
            },
            timeout=15,
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if not results:
            return None
        all_values = [float(v[1]) for r in results for v in r["values"] if v[1] != "NaN"]
        return max(all_values) if all_values else None
    except Exception:
        return None


def fmt(value: float | None, unit: str = "", decimals: int = 1) -> str:
    """Formata um valor numérico com unidade, ou '—' se None.

    Args:
        value: Valor numérico a formatar, ou None.
        unit: Sufixo de unidade (ex: '%', 'GB').
        decimals: Casas decimais (padrão: 1).

    Returns:
        String formatada ou '—' se value for None.
    """
    if value is None or math.isnan(value):
        return "—"
    return f"{value:.{decimals}f}{unit}"


def send_telegram(message: str) -> None:
    """Envia mensagem formatada no Telegram.

    Args:
        message: Texto da mensagem em formato Markdown.

    Raises:
        SystemExit: Se o envio falhar (erro de rede ou status HTTP não-ok).
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        # Não logar a URL — contém o bot token
        print(f"Erro de conexão ao enviar Telegram: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)
    if not resp.ok:
        print(f"Erro ao enviar Telegram: status={resp.status_code}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Coleta métricas do Prometheus e envia relatório diário no Telegram."""
    now = datetime.now(tz=BRT)
    data_str = now.strftime("%d/%m/%Y")

    # VM
    cpu_max = query_range_max(
        "100 - (avg(irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
    )
    ram_pct_max = query_range_max(
        "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100"
    )
    ram_gb = query("node_memory_MemTotal_bytes")
    ram_gb_num = (ram_gb / 1024 / 1024 / 1024) if ram_gb else None

    disco_pct = query(
        "100 - (node_filesystem_avail_bytes{mountpoint='/mnt/fotos'}"
        " / node_filesystem_size_bytes{mountpoint='/mnt/fotos'} * 100)"
    )
    disco_livre_gb = query(
        "node_filesystem_avail_bytes{mountpoint='/mnt/fotos'} / 1024 / 1024 / 1024"
    )

    # API
    total_requests = query("sum(increase(http_requests_total[24h]))")
    pico_req_min = query_range_max("sum(rate(http_requests_total[1m])) * 60")
    total_erros = query("sum(increase(http_requests_total{status=~'5..'}[24h]))")
    latencia_p95 = query(
        "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1h])) by (le))"
    )

    # Sem séries 5xx no período = zero erros (e não "sem dados") quando houve tráfego
    if total_erros is None and total_requests is not None and total_requests > 0:
        total_erros = 0.0

    # Calcular taxa de erro
    taxa_erro_str = "—"
    if (
        total_requests is not None
        and total_erros is not None
        and total_requests > 0
    ):
        taxa = (total_erros / total_requests) * 100
        taxa_erro_str = f"{taxa:.2f}%"

    # Banco e Cache
    pg_connections = query("sum(pg_stat_activity_count{datname='argus_db'})")
    redis_hit_rate = query(
        "rate(redis_keyspace_hits_total[1h])"
        " / (rate(redis_keyspace_hits_total[1h]) + rate(redis_keyspace_misses_total[1h])) * 100"
    )

    # Montar mensagem
    ram_line = f"{fmt(ram_pct_max, '%')}"
    if ram_gb_num:
        ram_used = (ram_pct_max / 100 * ram_gb_num) if ram_pct_max else None
        ram_line = f"{fmt(ram_used, 'GB')} / {ram_gb_num:.0f}GB ({fmt(ram_pct_max, '%')} máx)"

    msg = f"""📊 *ARGUS AI — Relatório Diário*
📅 {data_str}

🖥️ *VM*
├── CPU máx: {fmt(cpu_max, '%')}
├── RAM máx: {ram_line}
└── Disco fotos: {fmt(disco_pct, '%')} ({fmt(disco_livre_gb, 'GB livres')})

📡 *API*
├── Total requests: {fmt(total_requests, '', 0)}
├── Pico: {fmt(pico_req_min, ' req/min', 0)}
├── Latência p95: {fmt(latencia_p95, 's')}
└── Erros 5xx: {fmt(total_erros, '', 0)} ({taxa_erro_str})

🗄️ *Banco e Cache*
├── Conexões PG: {fmt(pg_connections, '', 0)}
└── Redis hit rate: {fmt(redis_hit_rate, '%')}

🔗 [Ver dashboard completo](https://{DOMAIN}/grafana)"""

    send_telegram(msg)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')}] Relatório enviado com sucesso.")


if __name__ == "__main__":
    main()
