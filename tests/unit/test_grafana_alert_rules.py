"""Testes de regressão para o provisionamento de alertas do Grafana.

Sem `instant: true` na query, o datasource Prometheus roda como range query
(retorna série temporal) e a expressão `threshold` do Grafana rejeita esse
formato ("looks like time series data, only reduced data can be alerted
on"), fazendo a regra entrar em erro de execução permanente a cada avaliação.
Com `execErrState: Alerting` (usado nos alertas críticos), isso vira alerta
falso-positivo perpétuo — o incidente que motivou este teste.
"""

from pathlib import Path

import yaml

RULES_PATH = (
    Path(__file__).parents[2] / "monitoring" / "grafana" / "provisioning" / "alerting" / "rules.yml"
)


def _iter_prometheus_queries() -> list[tuple[str, dict]]:
    """Retorna (uid da regra, modelo da query) para cada query Prometheus.

    Exclui as entradas de expressão (`datasourceUid: __expr__`), que não são
    queries e não têm o campo `instant`.

    Returns:
        Lista de tuplas (uid, model) de cada `data` cujo datasource não é __expr__.
    """
    config = yaml.safe_load(RULES_PATH.read_text())
    queries: list[tuple[str, dict]] = []
    for group in config["groups"]:
        for rule in group["rules"]:
            for entry in rule["data"]:
                if entry["datasourceUid"] == "__expr__":
                    continue
                queries.append((rule["uid"], entry["model"]))
    return queries


def test_toda_query_prometheus_e_instant():
    """Toda query Prometheus usada em condição de alerta deve ser instant.

    Range query alimentando a expressão `threshold` quebra a avaliação da
    regra em TODA execução (erro permanente, não um outage real).
    """
    queries = _iter_prometheus_queries()
    assert queries, "esperava encontrar ao menos uma query Prometheus em rules.yml"

    sem_instant = [uid for uid, model in queries if model.get("instant") is not True]
    assert not sem_instant, f"regras sem instant:true (vão quebrar sempre): {sem_instant}"
