# ShortLab

ShortLab to lokalny, deterministyczny pipeline do codziennego generowania i publikacji krótkich animacji 2D (Shorts), z panelem review, półautomatyczną publikacją i metrykami dla YouTube/TikTok.

## Zakres MVP
- Generacja DSL -> render -> review/QC -> publikacja -> metryki.
- Deterministyczny render 2D (Skia-Python/Cairo) + FFmpeg.
- Lokalna infrastruktura: Postgres, Redis, MinIO (Docker Compose).
- Panel review: React + Vite.

## Szybki start (macOS M2 Pro)
1. Zainstaluj narzędzia bazowe:
   - `make setup-macos` (lub `make bootstrap` dla pełnego setupu)
2. Zainstaluj wersje runtime przez mise:
   - `mise trust`
   - `mise install`
2. Zweryfikuj środowisko:
   - `make verify`
3. Utwórz venv i zależności:
   - `make venv`
   - `make deps-py-uv` lub `make deps-py-poetry`
   - Jeśli pycairo nie ładuje się na ARM64: `make pycairo-arm`
   - Jeśli widzisz ostrzeżenie o `VIRTUAL_ENV`, wykonaj `deactivate` lub `unset VIRTUAL_ENV`
   - Jeśli zmieniasz wersję Pythona: `make deps-py-lock UV_LOCK_ARGS=--upgrade`
   - Jeśli masz `pyenv` w PATH, uruchamiaj polecenia przez `.venv/bin/python` lub Makefile
4. Uruchom infrastrukturę:
   - Docker Desktop zainstaluj manualnie (bootstrap pomija cask)
   - `make infra-up`
5. Uruchom API/worker/UI (gdy kod będzie gotowy):
   - `make api`
   - `make worker`
   - `make ui`
   - `make run-dev` – uruchamia API+UI+worker z domyślnymi portami i REDIS db=1

### Pipeline (MVP) – komendy operacyjne
- `make worker` – startuje workera RQ.
- `make worker-burst` – worker w trybie burst (przetwarza i kończy).
- `make enqueue` – wrzuca minimalny job (generacja DSL -> render).
  - Idea Gate: najpierw wybierz pomysł z repozytorium (UI lub `make idea-gate`), potem uruchom enqueue z wybraną ideą.
- `make job-status` – pokazuje ostatnie joby.
- `make job-summary` – podsumowanie statusów jobów.
- `make job-failed` – lista jobów `failed` z payloadem błędu.
- `make cleanup-jobs OLDER_MIN=30` – oznacza stare joby `running` jako `failed`.
- `make purge-failed-jobs OLDER_MIN=60` – usuwa stare joby `failed`.
- `make cleanup-rq-failed` – czyści `failed` registry RQ (Redis), przydatne po starych/crashowanych jobach.
- `make idea-gate` – losuje propozycje z repo i wymusza klasyfikację (picked/later/rejected).
- `make qc-decide ANIMATION_ID=... QC_RESULT=accepted` – zapis decyzji QC.
- `make publish-record RENDER_ID=... PUBLISH_PLATFORM=youtube` – zapis publikacji.
- `make metrics-daily METRICS_CONTENT_ID=... METRICS_DATE=YYYY-MM-DD` – zapis metryk dziennych.
- `make metrics-pull-run METRICS_PLATFORM=youtube` – zapis uruchomienia pulla metryk.
- `make idea-generate` – generuje i zapisuje pomysły + embeddingi (tabela `idea_embedding`).
- `make idea-verify-capability` – weryfikuje wykonalność idei względem DSL i uzupełnia `dsl_gap`.
- `make dsl-gap-status DSL_GAP_ID=<UUID> DSL_GAP_STATUS=implemented` – aktualizuje status gapa i robi re-verification powiązanych idei.
- `IDEA_GEN_SOURCE=openai make idea-generate` – generuje pomysły przez OpenAI (wymaga `OPENAI_API_KEY`).
- Mediator LLM (routing per task) dla `idea_generate`:
  - `LLM_ROUTE_IDEA_GENERATE_PROVIDER=openai|openrouter|groq|litellm`
  - `LLM_ROUTE_IDEA_GENERATE_MODEL=<model>`
  - opcjonalnie `LLM_ROUTE_IDEA_GENERATE_BASE_URL`, `LLM_ROUTE_IDEA_GENERATE_API_KEY_ENV`
  - resiliency: `LLM_ROUTE_IDEA_GENERATE_TIMEOUT_S`, `..._RETRIES`, `..._BREAKER_*`
  - telemetria/cost estimate: `LLM_PRICE_DEFAULT_INPUT_PER_1K`, `LLM_PRICE_DEFAULT_OUTPUT_PER_1K`
  - safety caps: `LLM_ROUTE_IDEA_GENERATE_MAX_TOKENS`, `..._MAX_COST_USD`, `LLM_DAILY_BUDGET_USD`
  - persystencja metryk/budżetu: `LLM_MEDIATOR_STATE_FILE`
  - metryki runtime: `GET /llm/metrics` (operator-only)
- `make api` – uruchamia read‑only API (audit/metrics/idea embeddings).
  - `API_PORT=8010 make api` – zmiana portu (domyślnie 8000).
  - `OPERATOR_TOKEN=sekret make api` – włącza guard operatora dla `/ops/*`.
  - Jeśli pojawia się warning `nice(5) failed`, uruchom `make api` poza sandboxem (to ograniczenie środowiska, nie projektu).
- `make run-dev` – spójne uruchomienie API+UI+worker (PORT API=8016, UI=5173, REDIS db=1).
- `make run-dev` jest idempotentne: jeśli już działa, zwraca komunikat i exit 0.
- `make stop-dev` – zatrzymuje procesy uruchomione przez `make run-dev` i zwalnia porty API/UI.

### Operacje (API) – przykłady curl
Zakładając `OPERATOR_TOKEN=sekret`:
```bash
curl -sS -X POST http://localhost:8000/ops/enqueue \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Token: sekret' \
  -d '{"dsl_template":".ai/examples/dsl-v1-happy.yaml","out_root":"out/pipeline","idea_gate":false}'

curl -sS -X POST http://localhost:8000/ops/rerun \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Token: sekret' \
  -d '{"animation_id":"<UUID>","out_root":"out/pipeline"}'

curl -sS -X POST http://localhost:8000/ops/cleanup-jobs \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Token: sekret' \
  -d '{"older_min":30}'
```

### Pipeline (MVP) – minimalny flow
1. Uruchom infra: `make infra-up`
2. Zainstaluj deps (jeśli zmiany w `pyproject.toml`): `make deps-py-uv`
3. Start workera: `make worker`
4. Enqueue: `make enqueue`
5. Status: `make job-status` lub `make job-summary`

### Zmienne środowiskowe (.env)
- `DATABASE_URL` – połączenie do Postgresa.
- `REDIS_URL` – połączenie do Redis (RQ).
- `RQ_JOB_TIMEOUT` / `RQ_RENDER_TIMEOUT` – timeouty jobów w sekundach.
- `FFMPEG_TIMEOUT_S` – timeout ffmpeg w rendererze.
- `IDEA_GATE_COUNT` – liczba propozycji losowanych w Idea Gate.
- `OPENAI_API_KEY` – klucz do generatora pomysłów (opcjonalny).
- `OPENAI_MODEL` – model OpenAI dla generatora pomysłów (np. `gpt-4o-mini`).
- `OPENAI_BASE_URL` – endpoint API (domyślnie `https://api.openai.com/v1`).
- `OPENAI_TEMPERATURE` – temperatura generacji (domyślnie `0.7`).
- `OPENAI_MAX_OUTPUT_TOKENS` – limit tokenów odpowiedzi (domyślnie `800`).
- `ARTIFACTS_BASE_DIR` – katalog bazowy dla serwowania artefaktów (domyślnie `out`).
- `OPERATOR_TOKEN` – prosty token operatora dla endpointów `/ops/*` (nagłówek `X-Operator-Token`).
- `ALLOW_OPS_WITHOUT_TOKEN` – jeśli `1`, pozwala na `/ops/*` bez tokena (domyślnie `0`).

## Makefile
Dostępne cele:
- `make help` – lista targetów.
- `make doctor` – szybka diagnostyka środowiska.
- `make infra-up` / `infra-down` – Postgres/Redis/MinIO.
- `make db-reset` – resetuje schemat DB (drop + migrate, używa `DATABASE_URL`; jeśli brak psql, użyje kontenera Postgres z compose).

## Dokumentacja
- `/.ai/prd.md` – wymagania produktu.
- `/.ai/tech-stack.md` – stos technologiczny.
- `/.ai/bootstrap.md` – plan bootstrapu macOS.
- `/versions.env` – przypięte wersje narzędzi i usług.
- `/.ai/db-plan.md` – kanoniczny schemat bazy danych.

## Uwagi
- Renderer i FFmpeg uruchamiane natywnie na macOS dla stabilności i dostępności bibliotek.
- Zmiany wersji narzędzi powinny być wykonywane przez aktualizację `Brewfile` i lockfile.
- W razie zawieszeń renderu sprawdź `make job-summary` i użyj `make job-cleanup`.
  - Jeśli render wisi tylko w workerze, upewnij się, że używasz najnowszej wersji (ffmpeg z `-nostdin` + absolutne ścieżki).
