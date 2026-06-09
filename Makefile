.PHONY: check test lint

check: lint test

lint:
	uv run ruff check
	uv run mypy speclib/

test:
	uv run pytest -q
