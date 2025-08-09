.PHONY: lint fix format typecheck

PY = python3

lint:
	ruff check .

fix:
	ruff check --fix .
	ruff format .

format: fix

typecheck:
	mypy .
