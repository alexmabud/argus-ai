.PHONY: dev test lint migrate seed worker anonimizar

VENV_BIN := .venv/bin
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
	$(ALEMBIC) upgrade head

migrate-create:
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

seed:
	$(PYTHON) scripts/seed_legislacao.py
	$(PYTHON) scripts/seed_passagens.py

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
