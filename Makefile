.PHONY: install-local test lint build check

install-local:
	uv tool install --force .

test:
	uv run --extra dev pytest

lint:
	uv run --extra dev ruff check .

build:
	uv build --python 3.11

check: lint test build
