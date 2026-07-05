.PHONY: test lint typecheck format all

all: format lint typecheck test

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src tests
