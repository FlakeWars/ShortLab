SHELL := /bin/bash
-include .env
.DEFAULT_GOAL := help
export

PROJECT := shortlab
PYTHON ?= python3
VENV_DIR ?= .venv
VENV_BIN := $(VENV_DIR)/bin
PIP := $(VENV_BIN)/pip
UV_CMD := $(if $(wildcard $(VENV_BIN)/uv),$(VENV_BIN)/uv,uv)
UV_LOCK_ARGS ?=
POETRY := $(VENV_BIN)/poetry
DSL ?= .ai/examples/dsl-v1-happy.yaml
RENDER_OUT ?= out/render
RENDER_VIDEO ?= out/render.mp4
OLDER_MIN ?= 30
IDEA_GATE_SELECT ?=
IDEA_GATE_ENABLED ?= 0
IDEA_GATE_AUTO ?= 0
IDEA_GATE_SOURCE ?= auto
IDEA_GEN_SOURCE ?= file
IDEA_GEN_PATH ?= .ai/ideas.md
IDEA_GEN_LIMIT ?= 5
IDEA_GEN_SEED ?= 0
IDEA_GEN_PROMPT ?=
IDEA_GEN_SIM_THRESHOLD ?= 0.97
IDEA_VERIFY_LIMIT ?= 20
IDEA_VERIFY_ID ?=
IDEA_DSL_VERSION ?= v1
DSL_GAP_ID ?=
DSL_GAP_STATUS ?= accepted
QC_RESULT ?= accepted
QC_NOTES ?=
QC_DECIDED_BY ?=
ANIMATION_ID ?=
API_PORT ?= 8000
REDIS_URL_DEV ?= redis://localhost:6379/1
PUBLISH_PLATFORM ?= youtube
PUBLISH_STATUS ?= queued
PUBLISH_CONTENT_ID ?=
PUBLISH_URL ?=
PUBLISH_SCHEDULED_FOR ?=
PUBLISH_PUBLISHED_AT ?=
PUBLISH_ERROR ?=
METRICS_PLATFORM ?= youtube
METRICS_CONTENT_ID ?=
METRICS_DATE ?=
METRICS_VIEWS ?= 0
METRICS_LIKES ?= 0
METRICS_COMMENTS ?= 0
METRICS_SHARES ?= 0
METRICS_WATCH_TIME_SECONDS ?= 0
METRICS_AVG_VIEW_PERCENTAGE ?=
METRICS_AVG_VIEW_DURATION_SECONDS ?=
METRICS_PUBLISH_RECORD_ID ?=
METRICS_RENDER_ID ?=
METRICS_PULL_STATUS ?= queued
METRICS_PULL_SOURCE ?= api
METRICS_PULL_ERROR ?=


# Optional paths (adjust when code exists)
BACKEND_DIR ?= backend
FRONTEND_DIR ?= frontend
UI_PORT ?= 5173
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
		UV_CACHE_DIR=.uv-cache $(UV_CMD) sync --python "$(VENV_BIN)/python" --group dev; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: deps-py-lock
deps-py-lock: ## Update uv lockfile
	@if [ -f pyproject.toml ]; then \
		UV_CACHE_DIR=.uv-cache $(UV_CMD) lock --python "$(VENV_BIN)/python" $(UV_LOCK_ARGS); \
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

.PHONY: pycairo-arm
pycairo-arm: ## Rebuild pycairo from source for macOS ARM64
	@chmod +x ./scripts/install-pycairo-arm.sh
	@./scripts/install-pycairo-arm.sh

.PHONY: deps-frontend
deps-frontend: ## Install frontend deps (if frontend exists)
	@if [ -d $(FRONTEND_DIR) ]; then \
		cd $(FRONTEND_DIR) && npm install; \
	else \
		echo "$(FRONTEND_DIR) not found"; \
	fi

.PHONY: frontend-init
frontend-init: ## Initialize frontend (Vite + React + TS)
	@./scripts/init-frontend.sh "$(FRONTEND_DIR)" "react-ts"

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
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/uvicorn api.main:app --host 0.0.0.0 --port "$(API_PORT)"

.PHONY: worker
worker: ## Run worker process (placeholder)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/worker.py

.PHONY: worker-dev
worker-dev: ## Run worker with isolated Redis DB
	@REDIS_URL="$(REDIS_URL_DEV)" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/worker.py

.PHONY: worker-burst
worker-burst: ## Run worker in burst mode (process jobs then exit)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/worker.py --burst

.PHONY: scheduler
scheduler: ## Run scheduler (placeholder)
	@echo "Run scheduler (APScheduler)" 

.PHONY: enqueue
enqueue: ## Enqueue minimal pipeline job
	@IDEA_GATE_ENABLED="$(IDEA_GATE_ENABLED)" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/enqueue.py

.PHONY: enqueue-dev
enqueue-dev: ## Enqueue pipeline job with isolated Redis DB
	@REDIS_URL="$(REDIS_URL_DEV)" IDEA_GATE_ENABLED="$(IDEA_GATE_ENABLED)" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/enqueue.py

.PHONY: job-status
job-status: ## Show recent pipeline job statuses
	@REDIS_URL="$${REDIS_URL:-$(REDIS_URL_DEV)}" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py

.PHONY: job-status-dev
job-status-dev: ## Show job statuses with isolated Redis DB
	@REDIS_URL="$(REDIS_URL_DEV)" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py

.PHONY: job-summary
job-summary: ## Show job status summary
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py --summary

.PHONY: job-failed
job-failed: ## Show failed jobs with error payload
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/job-status.py --failed

.PHONY: cleanup-jobs
cleanup-jobs: ## Mark stale running jobs as failed
	@REDIS_URL="$${REDIS_URL:-$(REDIS_URL_DEV)}" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/cleanup-jobs.py --older-min "$(OLDER_MIN)"

.PHONY: purge-failed-jobs
purge-failed-jobs: ## Delete failed jobs older than OLDER_MIN
	@REDIS_URL="$${REDIS_URL:-$(REDIS_URL_DEV)}" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/purge-failed-jobs.py --older-min "$(OLDER_MIN)"

.PHONY: cleanup-rq-failed
cleanup-rq-failed: ## Delete failed jobs from RQ failed registry
	@REDIS_URL="$${REDIS_URL:-$(REDIS_URL_DEV)}" PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/cleanup-rq-failed.py --all

.PHONY: idea-generate
idea-generate: ## Generate ideas into DB (file/template)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-generate.py \
		--source "$(IDEA_GEN_SOURCE)" \
		--ideas-path "$(IDEA_GEN_PATH)" \
		--limit "$(IDEA_GEN_LIMIT)" \
		--seed "$(IDEA_GEN_SEED)" \
		--prompt "$(IDEA_GEN_PROMPT)" \
		--similarity-threshold "$(IDEA_GEN_SIM_THRESHOLD)"

.PHONY: idea-verify-capability
idea-verify-capability: ## Verify ideas against DSL capability (supports IDEA_VERIFY_ID)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-verify-capability.py \
		--limit "$(IDEA_VERIFY_LIMIT)" \
		--dsl-version "$(IDEA_DSL_VERSION)" \
		$(if $(IDEA_VERIFY_ID),--idea-id "$(IDEA_VERIFY_ID)",)

.PHONY: dsl-gap-status
dsl-gap-status: ## Update DSL gap status and reverify linked ideas (DSL_GAP_ID required)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/dsl-gap-status.py \
		--gap-id "$(DSL_GAP_ID)" \
		--status "$(DSL_GAP_STATUS)"

.PHONY: qc-decide
qc-decide: ## Create QC decision for an animation (ANIMATION_ID, QC_RESULT, QC_NOTES, QC_DECIDED_BY)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/qc-decide.py \
		--animation-id "$(ANIMATION_ID)" \
		--result "$(QC_RESULT)" \
		--notes "$(QC_NOTES)" \
		$(if $(QC_DECIDED_BY),--decided-by "$(QC_DECIDED_BY)",)

.PHONY: publish-record
publish-record: ## Create publish record (RENDER_ID, PUBLISH_PLATFORM, PUBLISH_STATUS, etc.)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/publish-record.py \
		--render-id "$(RENDER_ID)" \
		--platform "$(PUBLISH_PLATFORM)" \
		--status "$(PUBLISH_STATUS)" \
		$(if $(PUBLISH_CONTENT_ID),--content-id "$(PUBLISH_CONTENT_ID)",) \
		$(if $(PUBLISH_URL),--url "$(PUBLISH_URL)",) \
		$(if $(PUBLISH_SCHEDULED_FOR),--scheduled-for "$(PUBLISH_SCHEDULED_FOR)",) \
		$(if $(PUBLISH_PUBLISHED_AT),--published-at "$(PUBLISH_PUBLISHED_AT)",) \
		$(if $(PUBLISH_ERROR),--error "$(PUBLISH_ERROR)",)

.PHONY: metrics-daily
metrics-daily: ## Insert metrics_daily row (METRICS_* vars)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/metrics-daily.py \
		--platform "$(METRICS_PLATFORM)" \
		--content-id "$(METRICS_CONTENT_ID)" \
		--date "$(METRICS_DATE)" \
		--views "$(METRICS_VIEWS)" \
		--likes "$(METRICS_LIKES)" \
		--comments "$(METRICS_COMMENTS)" \
		--shares "$(METRICS_SHARES)" \
		--watch-time-seconds "$(METRICS_WATCH_TIME_SECONDS)" \
		$(if $(METRICS_AVG_VIEW_PERCENTAGE),--avg-view-percentage "$(METRICS_AVG_VIEW_PERCENTAGE)",) \
		$(if $(METRICS_AVG_VIEW_DURATION_SECONDS),--avg-view-duration-seconds "$(METRICS_AVG_VIEW_DURATION_SECONDS)",) \
		$(if $(METRICS_PUBLISH_RECORD_ID),--publish-record-id "$(METRICS_PUBLISH_RECORD_ID)",) \
		$(if $(METRICS_RENDER_ID),--render-id "$(METRICS_RENDER_ID)",)

.PHONY: metrics-pull-run
metrics-pull-run: ## Create metrics_pull_run row (METRICS_PULL_* vars)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/metrics-pull-run.py \
		--platform "$(METRICS_PLATFORM)" \
		--status "$(METRICS_PULL_STATUS)" \
		--source "$(METRICS_PULL_SOURCE)" \
		$(if $(METRICS_PULL_ERROR),--error "$(METRICS_PULL_ERROR)",)

.PHONY: db-stamp-head
db-stamp-head: ## Stamp alembic head (use when alembic_version points to removed revisions)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/alembic stamp head --purge

.PHONY: db-stamp-base
db-stamp-base: ## Stamp alembic base (empty DB state)
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/alembic stamp base --purge

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

.PHONY: llm-mediator-retention
llm-mediator-retention: ## Prune persisted LLM mediator metrics/budget rows
	@PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/llm-mediator-retention.py \
		--metrics-days "$${LLM_MEDIATOR_METRICS_RETENTION_DAYS:-30}" \
		--budget-days "$${LLM_MEDIATOR_BUDGET_RETENTION_DAYS:-120}"

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
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py --source "$(IDEA_GATE_SOURCE)" --select "$(IDEA_GATE_SELECT)"; \
	elif [ "$(IDEA_GATE_AUTO)" = "1" ]; then \
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py --source "$(IDEA_GATE_SOURCE)" --auto; \
	else \
		PYTHONPATH="$(PWD)" $(VENV_BIN)/python scripts/idea-gate.py --source "$(IDEA_GATE_SOURCE)"; \
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

.PHONY: db-reset
db-reset: ## Reset local database (drop schema + migrate)
	@./scripts/db-reset.sh

# --- Frontend ---
.PHONY: ui
ui: ## Run review panel (placeholder)
	@if [ -d $(FRONTEND_DIR) ]; then \
		cd $(FRONTEND_DIR) && npm run dev -- --host 0.0.0.0 --port "$(UI_PORT)"; \
	else \
		echo "$(FRONTEND_DIR) not found"; \
	fi

.PHONY: run-dev
run-dev: ## Run API + UI + worker with shared dev settings
	@API_PORT=8016 UI_PORT=5173 REDIS_URL=redis://localhost:6379/1 ./scripts/run-dev.sh

.PHONY: stop-dev
stop-dev: ## Stop processes started by run-dev
	@./scripts/stop-dev.sh

# --- Tests ---
.PHONY: test

test: ## Run all tests (placeholder)
	@if [ -f pyproject.toml ]; then \
		UV_CACHE_DIR=.uv-cache uv run -m pytest -q; \
	else \
		echo "pyproject.toml not found"; \
	fi

.PHONY: test-llm-mediator-db
test-llm-mediator-db: ## Run mediator persistence tests with required Postgres infra
	@chmod +x ./scripts/test-llm-mediator-db.sh
	@./scripts/test-llm-mediator-db.sh

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
	@echo "python: $$(command -v python || echo missing)"
	@echo "python -V: $$($(PYTHON) -V 2>/dev/null || echo missing)"
	@echo "VENV_DIR: $(VENV_DIR)"
	@echo ".venv python: $$($(VENV_BIN)/python -V 2>/dev/null || echo missing)"
	@echo "VIRTUAL_ENV: $${VIRTUAL_ENV:-unset}"
	@echo "Node: $$(node --version 2>/dev/null || echo 'missing')"
	@echo "FFmpeg: $$(ffmpeg -version 2>/dev/null | head -n 1 || echo 'missing')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'missing')"
