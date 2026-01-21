.PHONY: install lint typecheck

install:
	uv sync --group dev

lint:
	uv run --group dev pre-commit run --all-files

typecheck:
	uv run --group dev mypy .

test:
	uv run --group dev pytest

