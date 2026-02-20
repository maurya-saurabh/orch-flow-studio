.PHONY: help install install-dev install-hooks test test-cov test-fast test-one lint format check-format type-check clean all-checks build publish update-deps chainlit-dev chainlit-customer-support chainlit-sales chainlit-all node-red sanity file-server docker-build docker-build-no-cache docker-run docker-run-detached docker-up docker-down docker-logs docker-logs-compose docker-shell docker-stop docker-ps docker-restart docker-clean docker-remove docker-tag docker-push docker-pull docker-deploy docker-size

# Default target
help:
	@echo "Available commands:"
	@echo "  make install          - Install project dependencies"
	@echo "  make install-dev      - Install project with dev dependencies"
	@echo "  make install-hooks    - Install pre-commit hooks"
	@echo "  make test             - Run tests with coverage"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-fast        - Run tests without coverage"
	@echo "  make test-one         - Run specific test (usage: make test-one TEST=tests/test_file.py::test_func)"
	@echo "  make lint             - Run ruff linter with auto-fix"
	@echo "  make format           - Format code with ruff"
	@echo "  make check-format     - Check code formatting without modifying"
	@echo "  make type-check       - Run pyright type checker"
	@echo "  make all-checks       - Run all checks (format, type-check, test)"
	@echo "  make pre-commit       - Run pre-commit hooks on all files"
	@echo "  make clean            - Remove cache files and build artifacts"
	@echo "  make build            - Build the package"
	@echo "  make publish          - Publish package to PyPI"
	@echo "  make update-deps      - Update dependencies"
	@echo "  make chainlit-dev     - Run Orch Flow Studio Chainlit UI (port 2337)"
	@echo "  make chainlit-customer-support - Run Customer Support UI (port 1338)"
	@echo "  make chainlit-sales   - Run Sales UI (port 1339)"
	@echo "  make chainlit-all     - Run all domains simultaneously"
	@echo "  make node-red         - Start Node-RED with flows from src/node_red_flows (port 1880)"
	@echo ""
	@echo "Docker commands:"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-build-no-cache - Build Docker image without cache"
	@echo "  make docker-run       - Run container interactively"
	@echo "  make docker-run-detached - Run container in background"
	@echo "  make docker-up        - Start services with docker-compose"
	@echo "  make docker-down      - Stop services with docker-compose"
	@echo "  make docker-logs      - Show container logs"
	@echo "  make docker-logs-compose - Show docker-compose logs"
	@echo "  make docker-shell     - Open shell in container"
	@echo "  make docker-stop      - Stop running container"
	@echo "  make docker-ps        - List running containers"
	@echo "  make docker-restart   - Restart container"
	@echo "  make docker-clean     - Remove container and image"
	@echo "  make docker-remove    - Remove stopped containers"
	@echo "  make docker-tag       - Tag image for registry"
	@echo "  make docker-push      - Push image to registry"
	@echo "  make docker-pull      - Pull image from registry"
	@echo "  make docker-deploy    - Build and start with docker-compose"
	@echo "  make docker-size      - Show image size"

# Use system/global poetry and tools from parent venv
# VENV = ../.venv# MONOREPO
VENV = .venv# STANDALONE
PYTHON = $(VENV)/bin/python
POETRY = poetry
PRE_COMMIT = $(VENV)/bin/pre-commit
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff
PYRIGHT = $(VENV)/bin/pyright
CHAINLIT = $(VENV)/bin/chainlit

# Docker configuration
DOCKER_IMAGE_NAME = autobots-orch-flow-studio
DOCKER_IMAGE_TAG = latest
DOCKER_REGISTRY = # Set this to your registry (e.g., docker.io/username)
DOCKER_CONTAINER_NAME = autobots-orch-flow-studio

# Chainlit configuration
CHAINLIT_PORT = 2337
CHAINLIT_APP = src/autobots_orch_flow_studio/domains/orch_flow_studio/server.py
CHAINLIT_CUSTOMER_SUPPORT_PORT = 1338
CHAINLIT_CUSTOMER_SUPPORT_APP = src/autobots_orch_flow_studio/domains/customer_support/server.py
CHAINLIT_SALES_PORT = 1339
CHAINLIT_SALES_APP = src/autobots_orch_flow_studio/domains/sales/server.py

# Node-RED configuration (flows from src/node_red_flows)
NODE_RED_PORT = 1880
NODE_RED_USER_DIR = src/node_red_flows

# Install project dependencies
install:
	$(POETRY) install --only main

# Install project with dev dependencies
install-dev:
	$(POETRY) install --extras dev

# Install pre-commit hooks
install-hooks:
	$(PRE_COMMIT) install
	$(PRE_COMMIT) install --hook-type commit-msg

# Run tests with coverage
test:
	$(PYTEST)

# Run tests with coverage report
test-cov:
	$(PYTEST) --cov --cov-report=term-missing --cov-report=html

# Run tests without coverage (faster)
test-fast:
	$(PYTEST) --no-cov -x

# Run specific test
test-one:
	@if [ -z "$(TEST)" ]; then \
		echo "Usage: make test-one TEST=path/to/test_file.py::test_function"; \
	else \
		$(PYTEST) $(TEST); \
	fi

# Run ruff linter with auto-fix
lint:
	$(RUFF) check --fix .

# Format code with ruff
format:
	$(RUFF) format .

# Check code formatting without modifying
check-format:
	$(RUFF) format --check .
	$(RUFF) check .

# Run pyright type checker
type-check:
	$(PYRIGHT) src/

# Run all checks
all-checks: check-format type-check test

# Run pre-commit hooks on all files
pre-commit:
	$(PRE_COMMIT) run --all-files

# Clean cache and build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	rm -rf dist/ build/

# Build the package
build:
	$(POETRY) build

# Publish to PyPI (requires authentication)
publish:
	$(POETRY) publish

# Update dependencies
update-deps:
	$(POETRY) update

# Show outdated dependencies
show-outdated:
	$(POETRY) show --outdated

# Export requirements.txt
export-requirements:
	$(POETRY) export -f requirements.txt --output requirements.txt --without-hashes
	$(POETRY) export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes

# Run Orch Flow Studio Chainlit UI in development mode
chainlit-dev:
	PYTHONPATH=src DYNAGENT_CONFIG_ROOT_DIR=agent_configs/orch_flow_studio $(CHAINLIT) run $(CHAINLIT_APP) --port $(CHAINLIT_PORT) --host 127.0.0.1

# Run Customer Support Chainlit UI
chainlit-customer-support:
	DYNAGENT_CONFIG_ROOT_DIR=agent_configs/customer-support $(CHAINLIT) run $(CHAINLIT_CUSTOMER_SUPPORT_APP) --port $(CHAINLIT_CUSTOMER_SUPPORT_PORT) --host 127.0.0.1

# Run Sales Chainlit UI
chainlit-sales:
	DYNAGENT_CONFIG_ROOT_DIR=agent_configs/sales $(CHAINLIT) run $(CHAINLIT_SALES_APP) --port $(CHAINLIT_SALES_PORT) --host 127.0.0.1

# Run all domains simultaneously
chainlit-all:
	./sbin/run_all_domains.sh

# Start Node-RED with flows from src/node_red_flows (port 1880)
node-red:
	npx node-red -u $(NODE_RED_USER_DIR) --port $(NODE_RED_PORT)

# Run sanity tests
sanity:
	./sbin/sanity_test.sh

# Run file server
file-server:
	./sbin/run_file_server.sh

#
# Docker Commands
# Note: Docker build now uses local directory as context (autobots-devtools-shared-lib from PyPI)
#

# Build Docker image
docker-build:
	docker build -t $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) .

# Build Docker image without cache
docker-build-no-cache:
	docker build --no-cache -t $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) .

# Run container interactively (removes after exit)
docker-run:
	docker run --rm --name $(DOCKER_CONTAINER_NAME) -p $(CHAINLIT_PORT):$(CHAINLIT_PORT) $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Run container in background
docker-run-detached:
	docker run -d --name $(DOCKER_CONTAINER_NAME) -p $(CHAINLIT_PORT):$(CHAINLIT_PORT) $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Start services with docker-compose
docker-up:
	docker rm -f $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	docker-compose up -d

# Stop services with docker-compose
docker-down:
	docker-compose down

# Show container logs (standalone container)
docker-logs:
	docker logs -f $(DOCKER_CONTAINER_NAME)

# Show docker-compose logs
docker-logs-compose:
	docker-compose logs -f

# Open shell in running container
docker-shell:
	docker run --rm -it --entrypoint /bin/bash $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Stop running container
docker-stop:
	docker stop $(DOCKER_CONTAINER_NAME)

# List running containers
docker-ps:
	docker ps -a --filter "name=$(DOCKER_CONTAINER_NAME)"

# Restart container
docker-restart:
	docker restart $(DOCKER_CONTAINER_NAME)

# Remove container and image
docker-clean:
	docker rm -f $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	docker rmi $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) 2>/dev/null || true

# Remove stopped containers
docker-remove:
	docker rm $(DOCKER_CONTAINER_NAME) 2>/dev/null || true

# Tag image for registry
docker-tag:
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "Error: DOCKER_REGISTRY not set. Set it in Makefile or via: make docker-tag DOCKER_REGISTRY=docker.io/username"; \
		exit 1; \
	fi
	docker tag $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Push image to registry
docker-push: docker-tag
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "Error: DOCKER_REGISTRY not set. Set it in Makefile or via: make docker-push DOCKER_REGISTRY=docker.io/username"; \
		exit 1; \
	fi
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Pull image from registry
docker-pull:
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "Error: DOCKER_REGISTRY not set. Set it in Makefile or via: make docker-pull DOCKER_REGISTRY=docker.io/username"; \
		exit 1; \
	fi
	docker pull $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)

# Build and start with docker-compose (one command deployment)
docker-deploy:
	docker rm -f $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	docker-compose up -d --build

# Show image size
docker-size:
	docker images $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
