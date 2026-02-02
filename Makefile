SHELL := /bin/bash
-include .env
.DEFAULT_GOAL := help
export

PROJECT := shortlab
PYTHON ?= python3
VENV_DIR ?= .venv
VENV_BIN := $(VENV_DIR)/bin
PIP := $(VENV_BIN)/pip
UV := $(VENV_BIN)/uv
POETRY := $(VENV_BIN)/poetry
DSL ?= .ai/examples/dsl-v1-happy.yaml
RENDER_OUT ?= out/render
RENDER_VIDEO ?= out/render.mp4
OLDER_MIN ?= 30
IDEA_GATE_SELECT ?=
IDEA_GATE_AUTO ?= 0

# Optional paths (adjust when code exists)
BACKEND_DIR ?= backend
FRONTEND_DIR ?= frontend
DOCKER_BIN ?= docker
DOCKER_COMPOSE ?= $(DOCKER_BIN) compose

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "%-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- Bootstrap / setup ---
.PHONY: setup-macos
setup-macos: ## Run macOS bootstrap (Homebrew + tools)
	@./scripts/setup-macos.sh

.PHONY: bootstrap
bootstrap: setup-macos venv ## Prepare local environment (bootstrap)
	@echo "Bootstrap complete"

.PHONY: verify
verify: ## Verify local environment against pinned versions
	@./scripts/verify-env.sh

.PHONY: venv
venv: ## Create Python venv
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip

.PHONY: deps-py-uv
deps-py-uv: venv ## Install Python deps with uv (if lock exists)
	@if [ -f pyproject.toml ]; then \
		UV_CACHE_DIR=.uv-cache uv sync --group dev; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: deps-py-lock
deps-py-lock: ## Update uv lockfile
	@if [ -f pyproject.toml ]; then \
		UV_CACHE_DIR=.uv-cache uv lock; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: golden
golden: ## Regenerate golden hashes for renderer
	@UV_CACHE_DIR=.uv-cache uv run scripts/generate-golden.py

.PHONY: deps-py-poetry
deps-py-poetry: venv ## Install Python deps with poetry (if lock exists)
	@if [ -f pyproject.toml ]; then \
		$(POETRY) install; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: deps-frontend
deps-frontend: ## Install frontend deps (if frontend exists)
	@if [ -d $(FRONTEND_DIR) ]; then \
		cd $(FRONTEND_DIR) && npm install; \
	else \
		echo "$(FRONTEND_DIR) not found"; \
	fi

# --- Infra (Postgres/Redis/MinIO) ---
.PHONY: infra-up
infra-up: ## Start infra services via docker compose
	@$(DOCKER_COMPOSE) up -d

.PHONY: infra-down
infra-down: ## Stop infra services
	@$(DOCKER_COMPOSE) down

.PHONY: infra-logs
infra-logs: ## Tail infra logs
	@$(DOCKER_COMPOSE) logs -f --tail=200

# --- Backend API / workers ---
.PHONY: api
api: ## Run backend API (placeholder)
	@echo "Run backend API (FastAPI)" 

.PHONY: worker
worker: ## Run worker process (placeholder)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/worker.py

.PHONY: scheduler
scheduler: ## Run scheduler (placeholder)
	@echo "Run scheduler (APScheduler)" 

.PHONY: enqueue
enqueue: ## Enqueue minimal pipeline job
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/enqueue.py

.PHONY: job-status
job-status: ## Show recent pipeline job statuses
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py

.PHONY: job-summary
job-summary: ## Show job status summary
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py --summary

# --- Pipeline stages (PRD-aligned) ---
.PHONY: gen

gen: ## Generate DSL/spec (placeholder)
	@echo "Generate DSL spec" 

.PHONY: render
render: ## Render animation from DSL (placeholder)
	@UV_CACHE_DIR=.uv-cache uv run scripts/render-dsl.py --dsl "$(DSL)" --out-dir "$(RENDER_OUT)" --out-video "$(RENDER_VIDEO)"

.PHONY: review
review: ## Launch review UI (placeholder)
	@echo "Start review UI" 

.PHONY: publish
publish: ## Publish to platforms (placeholder)
	@echo "Publish to YouTube/TikTok" 

.PHONY: metrics
metrics: ## Pull platform metrics (placeholder)
	@echo "Pull metrics" 

.PHONY: qc
qc: ## Run QC checks (placeholder)
	@echo "Run QC checks" 

.PHONY: rerender
rerender: ## Rerender from metadata/seed (placeholder)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/rerun.py --animation-id "$(ANIMATION_ID)"

.PHONY: job-cleanup
job-cleanup: ## Mark stale running jobs as failed
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/cleanup-jobs.py --older-min "$(OLDER_MIN)"

.PHONY: idea-gate
idea-gate: ## Propose ideas and select one (Idea Gate)
	@if [ -n "$(IDEA_GATE_SELECT)" ]; then \
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py --select "$(IDEA_GATE_SELECT)"; \
	elif [ "$(IDEA_GATE_AUTO)" = "1" ]; then \
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py --auto; \
	else \
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py; \
	fi

# --- Data / exports ---
.PHONY: export
export: ## Export data for analysis (placeholder)
	@echo "Export data" 

# --- Database ---
.PHONY: db-migrate

db-migrate: ## Run DB migrations (placeholder)
	@if [ -x "$(VENV_BIN)/alembic" ]; then \
		$(VENV_BIN)/alembic upgrade head; \
	else \
		UV_CACHE_DIR=.uv-cache uv run alembic upgrade head; \
	fi

.PHONY: db-revision

db-revision: ## Create Alembic revision (set MSG="...") 
	@if [ -x "$(VENV_BIN)/alembic" ]; then \
		$(VENV_BIN)/alembic revision --autogenerate -m "$(MSG)"; \
	else \
		UV_CACHE_DIR=.uv-cache uv run alembic revision --autogenerate -m "$(MSG)"; \
	fi

.PHONY: db-seed

db-seed: ## Seed DB data (placeholder)
	@echo "Seed database" 

# --- Frontend ---
.PHONY: ui
ui: ## Run review panel (placeholder)
	@echo "Run frontend (Vite)" 

# --- Tests ---
.PHONY: test

test: ## Run all tests (placeholder)
	@if [ -f pyproject.toml ]; then \
		UV_CACHE_DIR=.uv-cache uv run -m pytest -q; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: test-render

test-render: ## Run render determinism tests (placeholder)
	@echo "Run render tests" 

.PHONY: test-ui

test-ui: ## Run UI smoke tests (Playwright) (placeholder)
	@echo "Run UI tests" 

# --- Lint/format ---
.PHONY: lint
lint: ## Run linters (placeholder)
	@echo "Run ruff/black" 

.PHONY: format
format: ## Format code (placeholder)
	@echo "Format code" 

# --- Dev convenience ---
.PHONY: doctor

doctor: ## Quick environment checks
	@echo "Python: $$($(PYTHON) --version 2>/dev/null || echo 'missing')"
	@echo "Node: $$(node --version 2>/dev/null || echo 'missing')"
	@echo "FFmpeg: $$(ffmpeg -version 2>/dev/null | head -n 1 || echo 'missing')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'missing')"
