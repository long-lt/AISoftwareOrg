# ==============================================================================
# Unified AI Software Factory — Makefile
# ==============================================================================
# Usage: make [target]
# Run `make help` to see all available targets.
# ==============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "  Unified AI Software Factory — Available Commands"
	@echo "  ================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ------------------------------------------------------------------------------
# Environment Setup
# ------------------------------------------------------------------------------
.PHONY: setup
setup: ## Create venv, install Python & Node dependencies
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install -e ".[dev]"
	cd frontend && npm install
	@echo ""
	@echo "✅ Setup complete. Run 'make dev' to start the server."

.PHONY: setup-frontend
setup-frontend: ## Install frontend dependencies only
	cd frontend && npm install

# ------------------------------------------------------------------------------
# Development
# ------------------------------------------------------------------------------
.PHONY: dev
dev: ## Run backend API server with hot-reload (port 8000)
	uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload

.PHONY: frontend
frontend: ## Run frontend dev server with Vite hot-reload (port 5173)
	cd frontend && npm run dev

.PHONY: start
start: ## Run full startup script (setup + build + server)
	bash run_factory.sh

# ------------------------------------------------------------------------------
# Build
# ------------------------------------------------------------------------------
.PHONY: build
build: ## Build frontend for production (outputs to frontend/dist/)
	cd frontend && npm run build

# ------------------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------------------
.PHONY: test
test: ## Run all tests with pytest
	pytest

.PHONY: test-verbose
test-verbose: ## Run all tests with verbose output
	pytest -v

.PHONY: test-dashboard
test-dashboard: ## Run dashboard & auth tests
	pytest tests/test_dashboard.py tests/test_dashboard_auth.py

.PHONY: test-rbac
test-rbac: ## Run RBAC tests
	pytest tests/test_rbac.py

.PHONY: test-workflow
test-workflow: ## Run workflow pipeline tests
	pytest tests/test_full_workflow.py

.PHONY: test-cost
test-cost: ## Run cost tracker tests
	pytest tests/test_cost_tracker.py

# ------------------------------------------------------------------------------
# Linting
# ------------------------------------------------------------------------------
.PHONY: lint
lint: ## Run ruff linter on Python code
	ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix .

# ------------------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------------------
.PHONY: docker-up
docker-up: ## Start Redis via Docker Compose
	docker-compose up -d

.PHONY: docker-down
docker-down: ## Stop Docker Compose services
	docker-compose down

# ------------------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove __pycache__, .pytest_cache, and log files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf htmlcov .coverage
	rm -f workspace/startup.log
	@echo "✅ Cleaned."
