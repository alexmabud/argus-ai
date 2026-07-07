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
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
        return None
    except Exception as exc:
        # Erro de conexão/HTTP/parse NÃO é "sem dados": registra em stderr para
        # não mascarar um Prometheus inacessível como métrica vazia no relatório.
        print(f"[reporter] erro ao consultar Prometheus ({promql!r}): {exc}", file=sys.stderr)
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


def backup_status(
    timestamp: float | None,
    scheduled_hour_brt: int,
    run_window_hours: float = 3.0,
) -> str:
    """Formata status de um backup agendado diariamente em scheduled_hour_brt.

    Em vez de um threshold fixo (que mascara uma execução perdida enquanto o
    último sucesso ainda estiver "recente"), valida se o backup ocorreu no
    slot agendado mais recente. Assim, se a execução de hoje não rodou, o
    relatório acusa ⚠️ ATRASADO já na manhã seguinte — mesmo que tenha havido
    um run manual avulso poucas horas antes.

    Args:
        timestamp: Unix timestamp (em segundos) do último backup OK, ou None.
        scheduled_hour_brt: Hora do agendamento diário em BRT (ex: 3 = 03h).
        run_window_hours: Folga após o horário agendado em que o backup ainda
            pode estar em execução (evita falso ATRASADO durante o run).

    Returns:
        String com emoji + status + tempo decorrido (ex: "✅ OK (8h atrás)").
    """
    if timestamp is None:
        return "❓ nunca registrado"
    now = datetime.now(tz=BRT)
    scheduled_today = now.replace(
        hour=scheduled_hour_brt, minute=0, second=0, microsecond=0
    )
    last_scheduled = (
        scheduled_today if scheduled_today <= now else scheduled_today - timedelta(days=1)
    )

    delta_h = (now.timestamp() - timestamp) / 3600
    if delta_h < 0:
        # Clock skew — trata como atual
        delta_h = 0
    if delta_h < 1:
        when = f"{int(delta_h * 60)}min atrás"
    elif delta_h < 48:
        when = f"{delta_h:.1f}h atrás"
    else:
        when = f"{int(delta_h / 24)}d atrás"

    ran_this_cycle = timestamp >= last_scheduled.timestamp()
    # Ainda dentro da janela de execução do slot atual: o backup pode estar
    # rodando agora; basta o ciclo anterior ter ido bem para não alarmar.
    within_run_window = (now - last_scheduled) <= timedelta(hours=run_window_hours)
    ran_prev_cycle = timestamp >= (last_scheduled - timedelta(days=1)).timestamp()

    if ran_this_cycle or (within_run_window and ran_prev_cycle):
        return f"✅ OK ({when})"
    return f"⚠️ ATRASADO ({when})"


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
        "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[24h])) by (le))"
    )
    # p95 médio de 24h dilui picos curtos entre centenas de requests rápidas do
    # dia. O pico em janelas de 5min é a mesma conta que o alerta de latência
    # usa — reflete os picos reais mesmo quando a média do dia parece ok.
    latencia_p95_pico = query_range_max(
        "histogram_quantile(0.95,"
        " sum(rate(http_request_duration_highr_seconds_bucket[5m])) by (le))"
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

    # Backup — valida o slot agendado mais recente (não um threshold fixo)
    # - Local (db-backup container): roda diariamente às 07h BRT
    # - Nuvens (backup_to_clouds.sh, cron root): roda às 03h BRT
    backup_local_ts = query("argus_backup_last_success_timestamp_seconds")
    backup_clouds_ts = query("argus_backup_clouds_last_success_timestamp_seconds")
    backup_local_status = backup_status(backup_local_ts, scheduled_hour_brt=7)
    backup_clouds_status = backup_status(backup_clouds_ts, scheduled_hour_brt=3)

    # Montar mensagem
    pico_alerta = " ⚠️" if latencia_p95_pico and latencia_p95_pico > 5 else ""
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
├── Latência p95 (24h): {fmt(latencia_p95, 's')}
├── Pico p95 (janela 5min): {fmt(latencia_p95_pico, 's')}{pico_alerta}
└── Erros 5xx: {fmt(total_erros, '', 0)} ({taxa_erro_str})

🗄️ *Banco e Cache*
├── Conexões PG: {fmt(pg_connections, '', 0)}
└── Redis hit rate: {fmt(redis_hit_rate, '%')}

💾 *Backup*
├── Local (banco): {backup_local_status}
└── Nuvens (Oracle + GDrive): {backup_clouds_status}

🔗 [Ver dashboard completo](https://{DOMAIN}/grafana)"""

    send_telegram(msg)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')}] Relatório enviado com sucesso.")


if __name__ == "__main__":
    main()
