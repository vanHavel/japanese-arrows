.PHONY: install lint typecheck test serve

install:
	uv sync --group dev

lint:
	uv run --group dev pre-commit run --all-files

typecheck:
	uv run --group dev mypy .

test-unit:
	uv run --group dev pytest tests/unit

test-integration:
	uv run --group dev pytest -n 7 -m "integration" tests/integration

test-all: test-unit test-integration

serve:
	uv run python -m http.server --directory web 8000

