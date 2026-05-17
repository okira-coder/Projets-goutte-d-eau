.PHONY: install ingest train api ui test lint format clean db-up db-shell db-init

install:
	python3.13 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

db-up:
	@echo "MVP local : SQLite, rien à démarrer. Prod : 'brew services start mysql'"

db-shell:
	sqlite3 data/goutte_eau.db

db-init:
	mkdir -p data
	sqlite3 data/goutte_eau.db < db/schema_sqlite.sql

db-init-mysql:
	mysql -u root < db/schema.sql
	mysql -u root goutte_eau < db/seeds/stations_occitanie.sql

ingest:
	. .venv/bin/activate && python -m src.ingestion.ingest_job

train:
	. .venv/bin/activate && python -m src.models.train

api:
	. .venv/bin/activate && uvicorn src.api.main:app --reload --port 8000

ui:
	. .venv/bin/activate && streamlit run streamlit_app/app.py

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check src tests && black --check src tests

format:
	. .venv/bin/activate && ruff check --fix src tests && black src tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
