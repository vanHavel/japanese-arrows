.PHONY: install lint typecheck test serve

install:
	uv sync --group dev

lint:
	uv run --group dev pre-commit run --all-files

typecheck:
	uv run --group dev mypy .

test:
	uv run --group dev pytest

serve:
	uv run python -m http.server --directory web 8000

