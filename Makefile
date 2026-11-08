.DEFAULT_GOAL := help
.PHONY: help check fmt test cov up down logs

help: ## Lista os comandos
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'

check: ## ruff, mypy e import-linter (igual ao job quality)
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run lint-imports

fmt: ## Formata e aplica correções do ruff
	uv run ruff check --fix .
	uv run ruff format .

test: ## Unitários (sem Docker)
	uv run pytest -m unit

cov: ## Unitários + integração com as duas metas de cobertura (precisa de postgres e redis)
	uv run pytest -m "unit or integration" --cov --cov-report=
	uv run coverage report --fail-under=85
	uv run coverage report --include="app/domain/*,app/application/*" --fail-under=100

up: ## Sobe o ambiente completo
	docker compose up -d --build --wait

down: ## Derruba o ambiente
	docker compose down

logs: ## Acompanha os logs
	docker compose logs -f
