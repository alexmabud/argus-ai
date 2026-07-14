"""Testes de regressão para o `docker-compose.prod.yml`.

Sem `container_name` explícito, o Docker Compose nomeia o container como
`<projeto>-<serviço>-<índice>`. Isso funciona para serviços com nome simples
(``worker`` -> ``argus-ai-worker-1``), mas quebra para ``worker-2``: o nome já
termina em número, então o índice do Compose se soma a ele e o container real
vira ``argus-ai-worker-2-1`` — divergente do que a documentação de
monitoramento, os scripts operacionais e a descrição do alerta
``alert-worker-parado`` esperam (``argus-ai-worker-1``/``argus-ai-worker-2``),
quebrando silenciosamente qualquer `docker logs`/`restart` manual apontado
para o nome "óbvio".
"""

from pathlib import Path

import yaml

COMPOSE_PATH = Path(__file__).parents[2] / "docker-compose.prod.yml"


def test_workers_tem_container_name_explicito():
    """Os dois serviços de worker precisam de `container_name` fixo.

    Sem isso, o serviço `worker-2` produz o container `argus-ai-worker-2-1`
    (nome duplo-indexado) em vez de `argus-ai-worker-2`, quebrando a
    convenção usada em toda a documentação/scripts operacionais.
    """
    config = yaml.safe_load(COMPOSE_PATH.read_text())
    services = config["services"]

    assert services["worker"].get("container_name") == "argus-ai-worker-1"
    assert services["worker-2"].get("container_name") == "argus-ai-worker-2"
