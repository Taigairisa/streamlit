# Simple helpers for local Docker dev

.PHONY: lint fix format typecheck run build  

APP := kakeibo-flask
CFG := fly.flask.toml
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

# Flask App Docker Commands
docker-build-flask:
	docker build -t kakeibo-flask -f Dockerfile.flask .

docker-run-flask:
	docker run -d --name kakeibo-flask-app -p 5000:5000 -v /home/taiga/code/kakeibo_st/runtime-data:/data kakeibo-flask

docker-ps:
	docker ps
docker-stop-flask:
	docker stop kakeibo-flask-app && docker rm kakeibo-flask-app 

# BuildKit OFF (legacy builder)
docker-build-flask-legacy:
	DOCKER_BUILDKIT=0 docker build -t kakeibo-flask -f Dockerfile.flask .

# Clean build: prune builder cache and build without cache
docker-build-flask-clean:
	-@docker builder prune -af >/dev/null 2>&1 || true
	docker build --no-cache -t kakeibo-flask -f Dockerfile.flask .

deploy:        ## fly deploy (local build)
	flyctl deploy -c $(CFG) --local-only -a $(APP)