# Plano: Load Test do Argus AI (Capacity + Stress) — Setup e Execução

> **Status**: Pronto para executar
> **Estimativa**: ~4-5h de trabalho (setup) + ~1h30 de testes
> **Autor**: Sessão Claude prévia (2026-05-27)
> **Próxima sessão**: Pegar este plano e executar do começo

---

## 1. Contexto e Objetivo

O Argus AI hoje tem gauges no Grafana com zonas de cor calibradas por "chute educado":
- `Requests/s`: verde 0-2.5 / amarelo 2.5-5 / vermelho >5
- `Latência p95`: verde 0-500ms / amarelo 500ms-2s / vermelho >2s

Queremos descobrir os números **reais** da capacidade da VM Oracle Cloud que roda prod (ARM 4vCPU/24GB) e:
1. Saber quantos guardas simultâneos a API aguenta
2. Calibrar as zonas dos gauges fielmente
3. Identificar gargalos (CPU? DB? Worker?)

**Decisões já tomadas pelo usuário:**
- (A) Ambiente: docker-compose secundário **na mesma VM** de prod
- (B) Foto: **incluir** no teste (caminho completo)
- (C) Quando: rodar **agora** (sem usuários reais hoje)

---

## 2. Princípios de Segurança (Não Quebrar Nada)

### 2.1. Isolamento total do stack de loadtest

- **Containers** com prefixo `argus-loadtest-*` (prod usa `argus-ai-*`)
- **Network** Docker separada: `argus-loadtest-network`
- **Volumes** separados em `/mnt/banco/loadtest/` (prod usa `/mnt/banco/{postgres,redis,fotos}`)
- **Portas** diferentes: API 8001, Postgres 5433, Redis 6380 (prod: 80/443/5432/6379)
- **Database** com nome diferente: `argus_db_loadtest` (em PG separado, NÃO no mesmo PG do prod)
- **Redis DB** dedicado (instância separada, não compartilhada com prod)
- **R2 bucket** dedicado ou prefix path `loadtest/` para isolar fotos de teste

### 2.2. Safety checks obrigatórios antes de qualquer ação destrutiva

Todo comando que possa remover dados (volumes, fotos, banco) precisa de um **script wrapper** que:
1. `grep` no nome do container/volume/path por "loadtest" — se não casar, aborta
2. Confirma que `DOMAIN`/`DB_HOST` não apontam pro prod
3. Mostra o que vai apagar e pede `yes` interativo

### 2.3. Limite de recursos (cgroups via Docker)

Como vai rodar na mesma VM do prod, **cada container do loadtest tem hard limit**:
- API: max 2 CPUs, 4GB RAM
- Postgres: max 1 CPU, 2GB RAM
- Redis: max 0.5 CPU, 512MB RAM
- Worker: max 1 CPU, 2GB RAM

Garante que o loadtest **não pode** sufocar o prod por mais do que aceitamos.

### 2.4. Critérios de abort automático

Durante o teste, monitorar a cada 30s. **Aborta** (`make loadtest-down`) se qualquer um:
- VM total CPU > 95% por mais de 5 min
- VM total RAM > 95%
- Disco com <5GB livre
- Algum container do **prod** (prefixo `argus-ai-*`) **reinicia** ou cai em status unhealthy
- Alerta `firing` no Grafana relacionado ao prod

### 2.5. Não tocar no banco/redis/storage de prod

O loadtest **nunca** se conecta:
- Ao Postgres do prod (porta 5432, container `argus-ai-db-1`)
- Ao Redis do prod (porta 6379, container `argus-ai-redis-1`)
- À pasta `/mnt/banco/fotos` ou `/mnt/banco/postgres` ou `/mnt/banco/redis`

Validar isso na config do `docker-compose.loadtest.yml` antes de subir.

---

## 3. Pré-requisitos (checar antes de começar)

- [ ] Branch `main` atualizada localmente (`git pull origin main`)
- [ ] CI do último commit verde (sem deploys pendentes quebrados)
- [ ] Backup do prod do dia anterior existe (`ssh argus 'ls -la /mnt/banco/backups/ | tail -5'`)
- [ ] Sem alerta firing no Grafana
- [ ] Espaço em disco da VM > 20GB livre (`ssh argus 'df -h /mnt/banco'`)
- [ ] k6 instalado no PC do usuário (se for usar PC; mas como decidimos rodar na VM, k6 vai num container)

---

## 4. Fase 1 — Mudanças de Código (4 commits separados)

### Commit 1: Flag `RATE_LIMIT_ENABLED`

**Por quê**: rate limit por IP de 30/min vai matar o teste em 6 segundos. Precisa desligar **só no ambiente de loadtest**.

**Arquivos:**

`app/config.py` — adicionar:
```python
RATE_LIMIT_ENABLED: bool = True
```

`app/core/rate_limit.py` — wrap o limiter para virar no-op quando desligado:
```python
from contextlib import contextmanager

class _NoOpLimiter:
    """Limiter que não faz nada — usado em load test."""
    def limit(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(
        key_func=_get_real_client_ip,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        storage_uri=settings.REDIS_URL,
    )
else:
    limiter = _NoOpLimiter()
```

**Validação pós-commit:**
- [ ] Testes existentes passam (`make test`)
- [ ] Em prod, `RATE_LIMIT_ENABLED` continua `True` (default), comportamento idêntico
- [ ] Em loadtest, `.env.loadtest` define `RATE_LIMIT_ENABLED=false` → endpoints não decoram

### Commit 2: Marcador `is_load_test` para cleanup

**Por quê**: precisamos deletar os dados de teste depois, sem confundir com dados reais.

**Opções:**
- **(a)** Adicionar coluna `is_load_test BOOLEAN DEFAULT FALSE` nos models (migration Alembic) — invasivo
- **(b)** Convencionar nomes: usuários `teste_load_*`, pessoas com CPF iniciando `99999999` — não invasivo

**Decisão recomendada: (b)** — sem migration, cleanup por padrão de nome/CPF. Não toca em schema.

**Arquivos:** nenhum no app. A convenção fica documentada no `scripts/seed_load_test.py`.

### Commit 3: Script de seed

`scripts/seed_load_test.py` — cria dados de teste, gera tokens.

Conteúdo (esqueleto):
```python
"""Popula o banco de loadtest com usuários, pessoas e tokens.

Roda APENAS contra o banco argus_db_loadtest. Aborta se DB_NAME != argus_db_loadtest.

Cria:
    - 200 usuários teste_load_001..200, todos na mesma guarnição_id=1
    - 1000 pessoas fake (CPF 99999999XXX, nome aleatório PT-BR)
    - Exporta tokens JSON em tests/load/data/tokens.json
"""
import asyncio, json, os, sys
from pathlib import Path
from app.config import settings
from app.database.session import async_session
from app.services.usuario_service import UsuarioService
from app.services.pessoa_service import PessoaService
from app.core.security import create_access_token

# SAFETY CHECK
assert "loadtest" in settings.DATABASE_URL, "ABORT: DATABASE_URL não é de loadtest!"
assert settings.DATABASE_URL.split("/")[-1] == "argus_db_loadtest", \
    "ABORT: Database não é argus_db_loadtest!"

# ... resto do script
```

**Pontos críticos:**
- **Assert no topo** que aborta se não estiver no DB certo
- Senha dos usuários é fixa (ex: `loadtest_password_123`) — não usar pra prod jamais
- Tokens JWT com `exp` longo (ex: 30 dias) pra não precisar refresh durante o teste
- Roda dentro do container API: `docker exec argus-loadtest-api python scripts/seed_load_test.py`

### Commit 4: Script de cleanup

`scripts/cleanup_load_test.py` — wipe seguro do ambiente de teste.

```python
"""Limpa o ambiente de loadtest.

Apaga apenas registros que casam com os padrões de teste:
    - Usuários com nome iniciando "teste_load_"
    - Pessoas com CPF iniciando "99999999"
    - Abordagens criadas pelos usuários de teste
    - Fotos das abordagens de teste

Ignora dados reais. Aborta se DB_NAME != argus_db_loadtest.
"""
```

**Validação:**
- [ ] Rodar primeiro com `--dry-run` que mostra quantos registros vai apagar sem apagar
- [ ] Idempotente (rodar 2x não causa erro)
- [ ] Loga IDs apagados pra audit

---

## 5. Fase 2 — Arquivos de Infraestrutura

### 5.1. `docker-compose.loadtest.yml`

Stack isolada. Estrutura:

```yaml
services:
  loadtest-db:
    image: pgvector/pgvector:pg16
    container_name: argus-loadtest-db
    networks: [argus-loadtest-network]
    ports: ["127.0.0.1:5433:5432"]  # SÓ localhost
    environment:
      POSTGRES_DB: argus_db_loadtest
      POSTGRES_USER: argus_loadtest
      POSTGRES_PASSWORD: ${LOADTEST_DB_PASSWORD}
    volumes:
      - argus-loadtest-pgdata:/var/lib/postgresql/data
    deploy:
      resources:
        limits: { cpus: '1', memory: 2G }

  loadtest-redis:
    image: redis:7-alpine
    container_name: argus-loadtest-redis
    networks: [argus-loadtest-network]
    ports: ["127.0.0.1:6380:6379"]
    deploy:
      resources:
        limits: { cpus: '0.5', memory: 512M }

  loadtest-minio:
    # MinIO local para fotos — NÃO usa R2 pra evitar contaminar storage real
    image: minio/minio:latest
    container_name: argus-loadtest-minio
    networks: [argus-loadtest-network]
    ports: ["127.0.0.1:9100:9000"]
    environment:
      MINIO_ROOT_USER: loadtest
      MINIO_ROOT_PASSWORD: loadtest123
    command: server /data
    volumes:
      - argus-loadtest-miniodata:/data

  loadtest-api:
    build: .
    container_name: argus-loadtest-api
    networks: [argus-loadtest-network]
    ports: ["127.0.0.1:8001:8000"]
    env_file: .env.loadtest
    depends_on: [loadtest-db, loadtest-redis, loadtest-minio]
    deploy:
      resources:
        limits: { cpus: '2', memory: 4G }

  loadtest-worker:
    build: .
    container_name: argus-loadtest-worker
    networks: [argus-loadtest-network]
    env_file: .env.loadtest
    command: arq app.tasks.worker.WorkerSettings
    deploy:
      resources:
        limits: { cpus: '1', memory: 2G }

  loadtest-k6:
    image: grafana/k6:latest
    container_name: argus-loadtest-k6
    networks: [argus-loadtest-network]
    volumes:
      - ./tests/load:/scripts
    profiles: [k6]  # só sobe quando chamado explicitamente

networks:
  argus-loadtest-network:
    driver: bridge

volumes:
  argus-loadtest-pgdata:
  argus-loadtest-miniodata:
```

**Pontos críticos:**
- Todos os containers expõem portas só em `127.0.0.1` (não 0.0.0.0) — não acessível de fora da VM
- Network isolada — não conversa com `argus-network` do prod
- Hard limits de CPU/RAM em cada serviço

### 5.2. `.env.loadtest.example`

```env
# AMBIENTE DE LOAD TEST — NÃO USAR EM PROD
ENV=loadtest
DEBUG=true
TESTING=false

# Database (apontando pra loadtest-db, não pra prod!)
DATABASE_URL=postgresql+asyncpg://argus_loadtest:CHANGEME@loadtest-db:5432/argus_db_loadtest
LOADTEST_DB_PASSWORD=CHANGEME

# Redis (instância dedicada, não a do prod)
REDIS_URL=redis://loadtest-redis:6379/0

# MinIO local em vez de R2
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://loadtest-minio:9000
S3_ACCESS_KEY=loadtest
S3_SECRET_KEY=loadtest123
S3_BUCKET=argus-loadtest

# Rate limit OFF
RATE_LIMIT_ENABLED=false

# JWT — chave diferente da prod
SECRET_KEY=loadtest-only-secret-key-not-for-prod
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=43200  # 30 dias

# Encryption key — diferente da prod
ENCRYPTION_KEY=<gerar nova com scripts/generate_encryption_key.py>

# CORS aberto pra teste
CORS_ORIGINS=http://localhost:8001
TRUSTED_PROXIES=127.0.0.1
```

### 5.3. `scripts/loadtest_safety_check.sh`

Wrapper que **valida** antes de qualquer comando destrutivo:

```bash
#!/bin/bash
set -euo pipefail

# Aborta se algum container do prod estiver unhealthy
for c in argus-ai-api-1 argus-ai-db-1 argus-ai-redis-1; do
    status=$(docker inspect -f '{{.State.Health.Status}}' "$c" 2>/dev/null || echo "missing")
    if [ "$status" = "unhealthy" ]; then
        echo "ABORT: container do prod $c está unhealthy"
        exit 1
    fi
done

# Aborta se algum nome envolvido não tem "loadtest"
for name in "$@"; do
    if [[ "$name" != *"loadtest"* ]]; then
        echo "ABORT: alvo '$name' não contém 'loadtest' — pode ser prod"
        exit 1
    fi
done

echo "Safety check OK"
```

### 5.4. `Makefile` — alvos novos

```makefile
.PHONY: loadtest-up loadtest-down loadtest-seed loadtest-clean \
        loadtest-smoke loadtest-capacity loadtest-stress loadtest-status

loadtest-up:
	@bash scripts/loadtest_safety_check.sh argus-loadtest-db argus-loadtest-redis
	docker compose -f docker-compose.loadtest.yml up -d --build
	@echo "Aguardando 30s para serviços estabilizarem..."
	@sleep 30
	docker exec argus-loadtest-api alembic upgrade head
	@echo "✅ Stack de loadtest pronta em http://localhost:8001"

loadtest-seed:
	@bash scripts/loadtest_safety_check.sh argus-loadtest-api
	docker exec argus-loadtest-api python scripts/seed_load_test.py
	@echo "✅ 200 usuários + 1000 pessoas criados. Tokens em tests/load/data/tokens.json"

loadtest-smoke:
	docker compose -f docker-compose.loadtest.yml run --rm -T loadtest-k6 \
		run /scripts/01-smoke.js
	@echo "✅ Smoke test concluído. Veja relatório acima."

loadtest-capacity:
	@echo "⚠️  Capacity test vai rodar por 30 min. Monitor Grafana em paralelo."
	@read -p "Continuar? [y/N] " ans; [ "$$ans" = "y" ] || exit 1
	docker compose -f docker-compose.loadtest.yml run --rm -T loadtest-k6 \
		run /scripts/02-capacity.js
	@echo "✅ Capacity test concluído."

loadtest-stress:
	@echo "⚠️  Stress test vai rodar por 20 min até quebrar."
	@read -p "Continuar? [y/N] " ans; [ "$$ans" = "y" ] || exit 1
	docker compose -f docker-compose.loadtest.yml run --rm -T loadtest-k6 \
		run /scripts/03-stress.js
	@echo "✅ Stress test concluído."

loadtest-status:
	docker compose -f docker-compose.loadtest.yml ps
	@echo "---"
	docker stats --no-stream $$(docker compose -f docker-compose.loadtest.yml ps -q)

loadtest-clean:
	@bash scripts/loadtest_safety_check.sh argus-loadtest-api
	docker exec argus-loadtest-api python scripts/cleanup_load_test.py
	@echo "✅ Dados de teste removidos"

loadtest-down:
	@bash scripts/loadtest_safety_check.sh argus-loadtest-db argus-loadtest-redis
	docker compose -f docker-compose.loadtest.yml down -v
	@echo "✅ Stack de loadtest derrubada. Volumes apagados."
```

---

## 6. Fase 3 — Scripts k6

### 6.1. `tests/load/k6.config.js` — base

```javascript
import { check } from 'k6';
import http from 'k6/http';

export const BASE_URL = __ENV.BASE_URL || 'http://loadtest-api:8000';

// Carregar tokens gerados pelo seed
export const tokens = JSON.parse(open('/scripts/data/tokens.json'));

// Pegar token aleatório (cada VU pega um)
export function getToken(vuId) {
    return tokens[(vuId - 1) % tokens.length];
}

export function authHeaders(token) {
    return { headers: { Authorization: `Bearer ${token}` } };
}

// Métricas customizadas globais
import { Trend, Rate } from 'k6/metrics';
export const errorRate = new Rate('errors');
export const latencyAbordagem = new Trend('latency_abordagem');
export const latencyBusca = new Trend('latency_busca');
```

### 6.2. `tests/load/01-smoke.js` — sanity (1 min, 5 VUs)

```javascript
import { sleep, check } from 'k6';
import http from 'k6/http';
import { BASE_URL, getToken, authHeaders } from './k6.config.js';

export const options = {
    vus: 5,
    duration: '1m',
    thresholds: {
        http_req_failed: ['rate<0.01'],  // <1% de erro
        http_req_duration: ['p(95)<1000'],  // p95 <1s
    },
};

export default function() {
    const token = getToken(__VU);
    const r = http.get(`${BASE_URL}/health`, authHeaders(token));
    check(r, { 'status 200': (r) => r.status === 200 });
    sleep(1);
}
```

### 6.3. `tests/load/02-capacity.js` — capacity (30 min, 0→200 VUs)

```javascript
import { sleep, check } from 'k6';
import http from 'k6/http';
import { BASE_URL, getToken, authHeaders, errorRate, latencyAbordagem } from './k6.config.js';

export const options = {
    stages: [
        { duration: '5m', target: 50 },    // warm-up
        { duration: '10m', target: 100 },  // load médio
        { duration: '10m', target: 200 },  // peak
        { duration: '5m', target: 0 },     // ramp-down
    ],
    thresholds: {
        http_req_failed: ['rate<0.05'],     // <5% erros = aborta
        http_req_duration: ['p(95)<5000'],  // p95 <5s = aborta
    },
};

export default function() {
    const token = getToken(__VU);
    const h = authHeaders(token);

    // 1. Buscar pessoa por nome
    const busca = http.get(`${BASE_URL}/api/v1/pessoas?nome=Silva`, h);
    check(busca, { 'busca 200': (r) => r.status === 200 });
    sleep(2);

    // 2. Criar pessoa nova (CPF 99999999XXX random)
    const cpf = `99999999${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`;
    const pessoa = http.post(`${BASE_URL}/api/v1/pessoas`, JSON.stringify({
        nome: `Teste Load ${__VU}-${__ITER}`,
        cpf: cpf,
        nome_mae: 'Maria Teste',
        endereco: 'Rua Teste 123',
        data_nascimento: '1990-01-01',
    }), { ...h, headers: { ...h.headers, 'Content-Type': 'application/json' } });

    if (pessoa.status !== 201) { errorRate.add(1); return; }
    const pessoaId = pessoa.json('id');
    sleep(5);

    // 3. Criar abordagem
    const t0 = Date.now();
    const abord = http.post(`${BASE_URL}/api/v1/abordagens`, JSON.stringify({
        data_hora: new Date().toISOString(),
        latitude: -15.7942 + (Math.random() - 0.5) * 0.1,
        longitude: -47.8822 + (Math.random() - 0.5) * 0.1,
        observacao: 'Load test',
        pessoa_ids: [pessoaId],
    }), { ...h, headers: { ...h.headers, 'Content-Type': 'application/json' } });
    latencyAbordagem.add(Date.now() - t0);
    check(abord, { 'abord 201': (r) => r.status === 201 });

    if (abord.status === 201) {
        // 4. Upload de foto (multipart)
        const photo = open('/scripts/data/sample-photo.jpg', 'b');
        const fd = { file: http.file(photo, 'sample.jpg', 'image/jpeg'),
                     abordagem_id: abord.json('id') };
        http.post(`${BASE_URL}/api/v1/fotos`, fd, h);
    }

    sleep(Math.random() * 20 + 10);  // think time 10-30s (guarda real)
}
```

### 6.4. `tests/load/03-stress.js` — stress (20 min, 0→500 VUs, sem think time)

Mesma estrutura mas:
- `stages`: 0→100 em 3min, 100→300 em 5min, 300→500 em 5min, 500→0 em 7min
- **Remove os `sleep()`** — manda request o mais rápido possível
- Threshold: `http_req_failed: ['rate<0.10']` (10% erro = limite máximo)

### 6.5. `tests/load/data/sample-photo.jpg`

Imagem JPEG real, pequena (~100-200KB), 800x600 px. Pode usar uma foto stock genérica de paisagem. **Importante**: ser uma imagem JPEG válida com magic bytes corretos (vai passar validação no upload).

### 6.6. `tests/load/README.md`

Documenta:
- Como rodar cada teste
- Como ler os resultados do k6
- Como cruzar com Grafana
- Como ajustar zonas dos gauges com base nos números

---

## 7. Fase 4 — Execução (Passo a Passo)

### 7.1. Pré-flight (no PC, antes de mexer na VM)

```bash
# 1. Pull código atualizado
cd ~/Projetos/argus_ai
git checkout main && git pull

# 2. Confirmar que os 4 commits da Fase 1 estão na main
git log --oneline -10

# 3. Confirmar que CI passou
gh run list --limit 3
```

### 7.2. Subir stack de loadtest (na VM)

```bash
ssh argus

# 1. Pull código na VM
cd ~/argus-ai
git pull origin main

# 2. Copiar .env.loadtest.example pra .env.loadtest
cp .env.loadtest.example .env.loadtest

# 3. Gerar secrets pro .env.loadtest
echo "LOADTEST_DB_PASSWORD=$(openssl rand -hex 16)" >> .env.loadtest
echo "ENCRYPTION_KEY=$(python scripts/generate_encryption_key.py)" >> .env.loadtest
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env.loadtest

# 4. Subir stack
make loadtest-up

# 5. Confirmar
make loadtest-status
```

**Validação:**
- [ ] Todos os 5 containers loadtest em `Up` status
- [ ] Containers do prod (`argus-ai-*`) **continuam** rodando normalmente
- [ ] `curl http://localhost:8001/health` retorna 200

### 7.3. Popular dados

```bash
make loadtest-seed
```

**Saída esperada:**
```
✅ Criados 200 usuários teste_load_001..200
✅ Criadas 1000 pessoas com CPF 99999999XXX
✅ 200 tokens exportados em tests/load/data/tokens.json
```

**Validação:**
- [ ] Arquivo `tests/load/data/tokens.json` existe com 200 entradas
- [ ] `docker exec argus-loadtest-db psql -U argus_loadtest -d argus_db_loadtest -c "SELECT COUNT(*) FROM usuarios"` retorna 201 (200 teste + admin)

### 7.4. Smoke test (1 min)

```bash
make loadtest-smoke
```

**Critério de sucesso:**
- 0% de erros (`http_req_failed`)
- p95 < 1s
- Todas as checks passaram

**Se falhar:** **PARAR**. Investigar antes de continuar. Logs em:
```bash
docker logs argus-loadtest-api --tail 100
docker logs argus-loadtest-worker --tail 100
```

### 7.5. Capacity test (30 min) — **EM PARALELO COM GRAFANA**

Abra duas janelas:
1. Terminal: `make loadtest-capacity`
2. Browser: Grafana dashboard "Argus AI — Performance" com refresh 30s

**Durante a execução, observe:**
- Gauge "CPU" e "RAM" — onde ficam quando estabiliza em 200 VUs?
- Gauge "Latência p95" — passa de 500ms? De 2s?
- Gauge "Requests/s" — quanto chega?
- Painel "Comandos Redis/s" — worker está conseguindo processar?
- Logs do prod (outra aba terminal): `ssh argus 'docker logs argus-ai-api-1 --tail 50 -f'` — **prod NÃO deve estar reclamando**

**Anotar no fim:**
- VUs em que latência p95 passou de 500ms → futuro "amarelo"
- VUs em que latência p95 passou de 2s → futuro "vermelho"
- VUs em que erros começaram → confirma "vermelho"
- Pico de req/s no Prometheus durante a fase de 200 VUs

### 7.6. Stress test (20 min)

```bash
make loadtest-stress
```

**Critério de "quebrou":**
- p95 > 5s consistente
- Erros > 10%
- API começa a retornar 503/504

**Anotar:**
- VUs no momento da quebra
- req/s atingido no momento da quebra
- Onde o gargalo estava (CPU? worker? DB?)

### 7.7. Calibração dos gauges

Com os números coletados, editar `monitoring/grafana/dashboards/argus-main.json`:

```json
// Gauge Requests/s — substituir thresholds
"thresholds": [
    { "color": "green",  "value": null },
    { "color": "yellow", "value": <REQ_S_MEDIO_DO_CAPACITY> },
    { "color": "red",    "value": <REQ_S_QUEBROU_NO_STRESS> }
]
"max": <2 * REQ_S_QUEBROU_NO_STRESS>
```

Commit a mudança em branch separada (`fix/calibrate-gauges-after-loadtest`) e abrir PR pra revisão antes de merge.

---

## 8. Fase 5 — Cleanup

```bash
# 1. Apagar dados de teste (mas mantém stack rodando, útil pra rodar mais cenários)
make loadtest-clean

# 2. Derrubar stack inteira + volumes
make loadtest-down

# 3. Validar
docker ps | grep loadtest    # não deve retornar nada
docker volume ls | grep loadtest  # não deve retornar nada
ls /mnt/banco/ | grep loadtest    # não deve retornar nada

# 4. Confirmar prod intacto
docker ps | grep argus-ai-
curl https://arguseye.duckdns.org/health
```

---

## 9. Plano de Rollback / Contingências

### Cenário A: Stack de loadtest não sobe
- Causa provável: porta em conflito, env var faltando
- Ação: `make loadtest-down`, ajustar `.env.loadtest`, tentar de novo
- Prod nunca foi tocado, sem impacto

### Cenário B: Loadtest derruba o prod
- Sintoma: alerta firing no Grafana, container do prod reiniciou
- Ação imediata:
  ```bash
  make loadtest-down   # mata loadtest
  ssh argus 'docker compose -f docker-compose.prod.yml restart api worker'  # restart prod
  ```
- Investigar: revisar limits de CPU/RAM no compose, dimensionar pra menos VUs no próximo round

### Cenário C: Migração falhou ao subir loadtest
- Causa: schema do prod tem migrations não aplicadas, ou conflito
- Ação: revisar `alembic history`, aplicar manualmente
- Não impacta prod (banco separado)

### Cenário D: Cleanup deletou dados de produção
- **Não deveria acontecer** com os safety checks, mas: tem backup em Oracle Object Storage
- Restore: `bash scripts/backup_rclone.sh --restore --date=2026-05-27`

---

## 10. Critérios de Pronto

Considera-se "load test concluído com sucesso" quando:

- [ ] Smoke + Capacity + Stress rodaram sem alerta firing no prod
- [ ] Coletados números: VUs max suportados, req/s max, latência por nível
- [ ] Identificado gargalo principal (CPU? DB? Worker?)
- [ ] Gauges do Grafana recalibrados com valores reais
- [ ] Stack de loadtest derrubada e ambiente limpo
- [ ] PR de calibração dos gauges aprovado e merged
- [ ] Documentado em `docs/load-test-results-2026-05-XX.md`:
  - Setup usado (VM size, container limits)
  - Números coletados
  - Próximas ações (upgrade de VM? otimizar query X?)

---

## 11. Anexos

### A. Comandos de monitoramento durante teste (cole numa aba terminal)

```bash
# Painel ao vivo na VM
watch -n 5 'docker stats --no-stream | grep -E "(argus-loadtest|argus-ai)"'

# Logs do prod em tempo real
ssh argus 'docker logs argus-ai-api-1 --tail 20 -f'

# Logs do loadtest em tempo real
ssh argus 'docker logs argus-loadtest-api --tail 20 -f'

# Métricas brutas do Prometheus
curl -s http://localhost:9090/api/v1/query?query='sum(rate(http_requests_total[1m]))' | jq
```

### B. Endpoints relevantes da API (de `app/api/v1/`)

| Endpoint | Método | Rate limit atual | Usado no teste? |
|---|---|---|---|
| `/health` | GET | — | Smoke |
| `/api/v1/auth/login` | POST | 10/min | Não (usa tokens pré-gerados) |
| `/api/v1/pessoas` | POST | 60/min default | ✅ |
| `/api/v1/pessoas?nome=` | GET | 60/min default | ✅ |
| `/api/v1/abordagens` | POST | 30/min | ✅ |
| `/api/v1/fotos` | POST | varia | ✅ |

### C. Tabela de tradução VUs → req/s (estimativa antes do teste)

| VUs | think time | Cadência média por VU | Total req/s |
|---|---|---|---|
| 50 | 10-30s | 0.05 req/s | ~2.5 |
| 100 | 10-30s | 0.05 req/s | ~5 |
| 200 | 10-30s | 0.05 req/s | ~10 |
| 500 (stress) | 0 | 5-20 req/s | 2500+ (vai quebrar antes) |

---

## 12. Como retomar do zero numa nova sessão Claude

Cole este prompt na nova sessão:

> "Tenho um plano detalhado de load test em `plans/load-test-setup.md`. Quero executar agora começando pela Fase 1 (mudanças de código). Lê o plano inteiro primeiro, depois me confirma o que vai fazer antes de tocar em qualquer arquivo. Princípio crítico: não pode quebrar produção em momento algum. Se em algum passo algo não bater com o plano, para e me consulta."

A nova sessão deve:
1. Ler este arquivo inteiro
2. Confirmar entendimento dos princípios de segurança (seção 2)
3. Executar Fase 1 commit a commit, validando cada um
4. Pedir confirmação antes de cada fase nova
5. Em caso de qualquer erro inesperado, parar e pedir orientação

---

**Fim do plano.**
