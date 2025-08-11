# Simple helpers for local Docker dev

.PHONY: lint fix format typecheck run build  

PY = python3

build:
	docker build -t myapp .

run:
	docker run --rm -p 8501:8501 -v "$(pwd)/WD/data:/data" myapp 

restart:
	$(MAKE) build && $(MAKE) run

lint:
	ruff check .

fix:
	ruff check --fix .
	ruff format .

format: fix

typecheck:
	mypy .
