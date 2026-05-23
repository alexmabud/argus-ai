.PHONY: dev test test-db lint migrate init-db seed worker anonimizar monitoring monitoring-local monitoring-down monitoring-logs monitoring-report-now

# Detecta Windows (Scripts) vs Linux/Mac (bin)
ifeq ($(OS),Windows_NT)
  VENV_BIN := .venv/Scripts
else
  VENV_BIN := .venv/bin
endif

PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
UVICORN := $(VENV_BIN)/uvicorn
ARQ := $(VENV_BIN)/arq
PYTEST := $(VENV_BIN)/pytest
RUFF := $(VENV_BIN)/ruff
MYPY := $(VENV_BIN)/mypy
ALEMBIC := $(VENV_BIN)/alembic

dev:
	docker compose up -d db redis minio
	$(UVICORN) app.main:app --reload

worker:
	$(ARQ) app.worker.WorkerSettings

# Garante que existe um banco argus_test isolado, com as extensions do projeto.
# Isso evita que o pytest (que dropa todas as tabelas em cada teste) destrua
# argus_db (dev) ou pior, um banco de produção se DATABASE_URL apontar para lá.
test-db:
	docker compose up -d db redis
	@docker compose exec -T db psql -U argus -d postgres -tAc \
		"SELECT 1 FROM pg_database WHERE datname='argus_test'" 2>/dev/null | grep -q 1 || \
		( \
			echo "Criando banco argus_test..." && \
			docker compose exec -T db psql -U argus -d postgres \
				-c "CREATE DATABASE argus_test TEMPLATE template0" && \
			docker compose exec -T db sh -c \
				"psql -U argus -d argus_test -f /docker-entrypoint-initdb.d/init.sql" \
		)

test: test-db
	DATABASE_URL=postgresql://argus:argus_dev@localhost:5432/argus_test $(PYTEST) -v --cov=app

lint:
	$(RUFF) check app/ tests/
	$(MYPY) app/ --ignore-missing-imports

format:
	$(RUFF) format app/ tests/

migrate:
	@if ls alembic/versions/*.py >/dev/null 2>&1; then \
		$(ALEMBIC) upgrade head; \
	else \
		echo "Sem migrations em alembic/versions; executando init-db."; \
		$(PYTHON) scripts/init_db.py; \
	fi

init-db:
	$(PYTHON) scripts/init_db.py

migrate-create:
	@test -n "$(msg)" || { echo "Uso: make migrate-create msg='descricao'"; exit 1; }
	$(ALEMBIC) revision --autogenerate -m '$(msg)'

seed:
	@if [ -f scripts/seed_passagens.py ]; then $(PYTHON) scripts/seed_passagens.py; else echo "scripts/seed_passagens.py nao existe; pulando seed de passagens."; fi

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api worker

encrypt-key:
	$(PYTHON) scripts/generate_encryption_key.py

anonimizar:
	$(PYTHON) scripts/anonimizar_dados.py

anonimizar-dry:
	$(PYTHON) scripts/anonimizar_dados.py --dry-run

# ─── Monitoramento ────────────────────────────────────────────────────────────

monitoring:
	@echo "Criando diretórios de dados em /mnt/banco..."
	sudo mkdir -p /mnt/banco/prometheus /mnt/banco/grafana
	sudo chown -R ubuntu:ubuntu /mnt/banco/prometheus /mnt/banco/grafana
	@echo "Subindo stack de monitoramento (Prometheus + Grafana + Exporters)..."
	docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml \
		up -d \
		prometheus grafana node-exporter cadvisor postgres-exporter redis-exporter telegram-reporter
	@echo "✅ Grafana disponível em: https://$$DOMAIN/grafana"
	@echo "   Login: admin / $$GF_ADMIN_PASSWORD"

monitoring-local:
	@echo "Subindo monitoramento em ambiente local..."
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml \
		up -d prometheus grafana node-exporter cadvisor postgres-exporter redis-exporter

monitoring-down:
	docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml \
		stop \
		prometheus grafana node-exporter cadvisor postgres-exporter redis-exporter telegram-reporter

monitoring-logs:
	docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml \
		logs -f prometheus grafana telegram-reporter

# Força o reporter a rodar agora (útil para testar sem esperar as 8h)
monitoring-report-now:
	docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml \
		exec telegram-reporter python /app/daily_report.py
