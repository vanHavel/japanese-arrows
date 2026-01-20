.PHONY: install lint typecheck

install:
	uv sync --group lint

lint:
	uv run --group lint pre-commit run --all-files

typecheck:
	uv run --group lint mypy .

test:
	uv run --group tests pytest

