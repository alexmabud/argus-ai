.PHONY: dev test lint migrate seed worker

dev:
	docker compose up -d db redis minio
	uvicorn app.main:app --reload

worker:
	arq app.worker.WorkerSettings

test:
	pytest -v --cov=app

lint:
	ruff check app/ tests/
	mypy app/ --ignore-missing-imports

format:
	ruff format app/ tests/

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python scripts/seed_legislacao.py
	python scripts/seed_passagens.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api worker

encrypt-key:
	python scripts/generate_encryption_key.py
