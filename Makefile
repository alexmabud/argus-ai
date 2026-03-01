.PHONY: dev test lint migrate init-db seed worker anonimizar

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

test:
	$(PYTEST) -v --cov=app

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
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

seed:
	$(PYTHON) scripts/seed_legislacao.py
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
