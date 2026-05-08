.PHONY: dev test test-db lint migrate init-db seed worker anonimizar

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
