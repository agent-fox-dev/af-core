.PHONY: check test lint clean

check: lint test

lint:
	uv run ruff check
	uv run mypy speclib/

test:
	uv run pytest -q

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[codz]' -delete 2>/dev/null || true
	find . -type f -name '*$$py.class' -delete 2>/dev/null || true
	rm -rf .pytest_cache .hypothesis .mypy_cache .ruff_cache
	rm -rf build dist *.egg-info .eggs
	rm -rf htmlcov .coverage .coverage.* coverage.xml
	rm -rf .tox .nox .cache
