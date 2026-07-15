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


def _find_rule(uid: str) -> dict:
    """Retorna a regra com o `uid` informado (falha se não existir)."""
    config = yaml.safe_load(RULES_PATH.read_text())
    for group in config["groups"]:
        for rule in group["rules"]:
            if rule["uid"] == uid:
                return rule
    raise AssertionError(f"regra '{uid}' não encontrada em rules.yml")


def test_worker_parado_nao_co_dispara_com_redis_down():
    """alert-worker-parado não deve disparar quando a causa raiz é o Redis caído.

    Revisão pós-#12/2026-07-13: app/core/worker_health.py grava
    argus_worker_alive=0 para TODOS os workers quando o Redis está
    inacessível (fail-closed) — sem gating por redis_up, este alerta
    co-dispara com alert-redis-down para o mesmo incidente, reintroduzindo a
    duplicidade/desdiagnóstico que a versão anterior à #12 evitava.
    """
    rule = _find_rule("alert-worker-parado")
    query_a = next(e["model"] for e in rule["data"] if e["model"]["refId"] == "A")
    expr = query_a["expr"]
    assert "argus_worker_alive" in expr
    assert "redis_up" in expr, "expr precisa de redis_up p/ não co-disparar com Redis Offline"


def test_worker_parado_casa_vetores_com_on_explicito():
    """A multiplicação em alert-worker-parado precisa de `on()` explícito.

    Achado 2026-07-15 (~21h de falso-positivo contínuo): `min(argus_worker_alive)`
    descarta todos os labels (min() sem `by()`), enquanto `redis_up` mantém
    `instance`/`job`. Sem `on()`/`ignoring()`, o casamento padrão de vetores do
    PromQL exige o MESMO conjunto de labels dos dois lados — um vazio, o outro
    não, nunca batem. A multiplicação retorna vetor vazio SEMPRE (confirmado
    ao vivo contra o Prometheus de produção), e com `noDataState: Alerting`
    isso dispara a regra em toda avaliação, para sempre, independente do
    estado real do worker/Redis.
    """
    rule = _find_rule("alert-worker-parado")
    query_a = next(e["model"] for e in rule["data"] if e["model"]["refId"] == "A")
    expr = query_a["expr"]
    assert "on()" in expr, (
        "sem `on()`, min(argus_worker_alive) (sem labels) * redis_up (com labels) "
        "nunca da match -- vetor vazio sempre, alerta perpetuo via noDataState"
    )


VALID_THRESHOLD_EVALUATORS = {"gt", "lt", "within_range", "outside_range"}


def test_toda_condicao_threshold_usa_avaliador_valido():
    """Todo `type: threshold` só aceita [gt, lt, within_range, outside_range].

    Achado 2026-07-15 (causa raiz real de ~21h de alerta preso em
    alert-worker-parado, anterior ao bug de vector matching): `gte`/`lte`
    NÃO existem no motor de expressão do Grafana. Usar um desses quebra a
    construção da regra em TODA avaliação ("failed to parse expression
    'threshold': ... got gte"), e com execErrState: Alerting isso força o
    estado Alerting permanentemente — mesmo com a query de dados saudável.
    O erro só aparece no log do Grafana, nunca na UI de forma óbvia.
    """
    config = yaml.safe_load(RULES_PATH.read_text())
    invalidos = []
    for group in config["groups"]:
        for rule in group["rules"]:
            for entry in rule["data"]:
                model = entry["model"]
                if model.get("type") != "threshold":
                    continue
                for condition in model.get("conditions", []):
                    tipo = condition["evaluator"]["type"]
                    if tipo not in VALID_THRESHOLD_EVALUATORS:
                        invalidos.append((rule["uid"], tipo))
    assert not invalidos, f"avaliadores invalidos (quebram a regra sempre): {invalidos}"
