.PHONY: help install dev test lint format eval clean

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies (uv sync)"
	@echo "  dev        Run local dev server"
	@echo "  test       Run unit + integration tests"
	@echo "  lint       Run ruff + mypy"
	@echo "  format     Run ruff format"
	@echo "  eval       Run evaluation harness (Promptfoo)"
	@echo "  clean      Remove build artifacts"

install:
	uv sync --all-extras

dev:
	uv run uvicorn radio_transforma.api.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check src tests
	uv run mypy src

format:
	uv run ruff format src tests

eval:
	cd evals && npx promptfoo@latest eval -c config/promptfoo.yaml

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +