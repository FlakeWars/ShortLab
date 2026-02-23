# ShortLab

ShortLab to lokalny pipeline do codziennego generowania i publikacji krótkich animacji 2D (Shorts), z panelem review, półautomatyczną publikacją i metrykami dla YouTube/TikTok. Nowy kierunek zaklada Godot 4.x + pelny GDScript generowany przez LLM (deterministycznosc nie jest celem nadrzednym).

## Zakres MVP
- Generacja pomyslu + skryptu GDScript -> walidacja/naprawa -> preview -> render -> review/QC -> publikacja -> metryki.
- Render 2D w Godot 4.x (Movie Maker) + opcjonalny FFmpeg.
- Lokalna infrastruktura: Postgres, Redis, MinIO (Docker Compose).
- Panel review: React + Vite.

## Stan implementacji (2026-02-11)
- Dziala legacy sciezka DSL: enqueue -> generate_dsl -> render -> artefakty.
- Dziala Idea Repository/Idea Gate + embeddings.
- Dziala mediator LLM z routingiem i persystencja metryk/budzetu w DB.
- Nowy kierunek: Godot 4.x + GDScript (LLM generuje pelny skrypt) — migracja w toku.
- W toku: pelna sciezka UI dla QC/publikacji/metryk.

## Szybki start (macOS M2 Pro)
1. Zainstaluj narzędzia bazowe:
   - `make setup-macos` (lub `make bootstrap` dla pełnego setupu)
2. Zainstaluj Godot 4.x (wersja w `versions.env`) przez Makefile:
   - `make godot-install`
3. Zainstaluj wersje runtime przez mise:
   - `mise trust`
   - `mise install`
4. Zweryfikuj środowisko:
   - `make verify`
5. Utwórz venv i zależności:
   - `make venv`
   - `make deps-py-uv` lub `make deps-py-poetry`
   - Jeśli pycairo nie ładuje się na ARM64: `make pycairo-arm`
   - Jeśli widzisz ostrzeżenie o `VIRTUAL_ENV`, wykonaj `deactivate` lub `unset VIRTUAL_ENV`
   - Jeśli zmieniasz wersję Pythona: `make deps-py-lock UV_LOCK_ARGS=--upgrade`
   - Jeśli masz `pyenv` w PATH, uruchamiaj polecenia przez `.venv/bin/python` lub Makefile
6. Uruchom infrastrukturę:
   - Docker Desktop zainstaluj manualnie (bootstrap pomija cask)
   - `make infra-up`
7. Uruchom API/worker/UI (gdy kod będzie gotowy):
   - `make api`
   - `make worker`
   - `make ui`
   - `make run-dev` – uruchamia API+UI+worker z domyślnymi portami i REDIS db=1

### Pipeline (legacy DSL) – komendy operacyjne
Uwaga: ponizsze komendy dotycza legacy sciezki DSL. Nowy pipeline Godot/GDScript jest w przygotowaniu.
- `make worker` – startuje workera RQ.
- `make worker-burst` – worker w trybie burst (przetwarza i kończy).
- `make enqueue` – wrzuca minimalny job (generacja DSL -> render).
  - Idea Gate: najpierw wybierz propozycję z repozytorium kandydatów (UI lub `make idea-gate`), potem uruchom enqueue z wybraną ideą.
- `make job-status` – pokazuje ostatnie joby.
- `make job-summary` – podsumowanie statusów jobów.
- `make job-failed` – lista jobów `failed` z payloadem błędu.
- `make cleanup-jobs OLDER_MIN=30` – oznacza stare joby `running` jako `failed`.
- `make purge-failed-jobs OLDER_MIN=60` – usuwa stare joby `failed`.
- `make cleanup-rq-failed` – czyści `failed` registry RQ (Redis), przydatne po starych/crashowanych jobach.
- `make idea-gate` – losuje propozycje z repo i wymusza klasyfikację (picked/later/rejected).
- `make idea-verify-capability` – weryfikuje wykonalność kandydatów względem DSL (obsługuje `IDEA_VERIFY_CANDIDATE_ID`).
- `make qc-decide ANIMATION_ID=... QC_RESULT=accepted` – zapis decyzji QC.
- `make publish-record RENDER_ID=... PUBLISH_PLATFORM=youtube` – zapis publikacji.
- `make metrics-daily METRICS_CONTENT_ID=... METRICS_DATE=YYYY-MM-DD` – zapis metryk dziennych.
- `make metrics-pull-run METRICS_PLATFORM=youtube` – zapis uruchomienia pulla metryk.
- `make llm-mediator-retention` – czyści historyczne metryki/budżet mediatora LLM (retention).
- `make test-llm-mediator-db` – uruchamia testy persystencji mediatora LLM z wymaganym Postgres (bez skipów integracyjnych).
- `make test-idea-compiler-pipeline-e2e` – uruchamia E2E kompilatora Idea->DSL+render; resetuje schemat DB do kanonicznego przed testem.
- `make idea-generate` – generuje i zapisuje pomysły + embeddingi (tabela `idea_embedding`).
- `make idea-verify-capability` – weryfikuje wykonalność kandydatów względem DSL i uzupełnia `dsl_gap`.
- `make dsl-gap-status DSL_GAP_ID=<UUID> DSL_GAP_STATUS=implemented` – aktualizuje status gapa i robi re-verification powiązanych idei.
- `make idea-compile-dsl IDEA_COMPILE_ID=<UUID>` – wymusza kompilację jednej idei do DSL (MVP compiler path).
- `IDEA_GEN_SOURCE=openai make idea-generate` – generuje pomysły przez OpenAI (wymaga `OPENAI_API_KEY`).
- Mediator LLM (routing per task) dla `idea_generate`:
  - profile tasków (bez zmian po stronie klientów):
    - `idea_generate` -> `creative`
    - `idea_verify_capability` -> `analytical`
    - `idea_compile_dsl` + `dsl_repair` -> `structured`
  - profile map: `LLM_TASK_PROFILE_<TASK>=creative|analytical|structured`
  - profile defaults: `LLM_PROFILE_<PROFILE>_*` (provider/model/timeout/retries/limits)
  - `LLM_ROUTE_IDEA_GENERATE_PROVIDER=openai|openrouter|groq|litellm`
  - `LLM_ROUTE_IDEA_GENERATE_MODEL=<model>`
  - opcjonalnie `LLM_ROUTE_IDEA_GENERATE_BASE_URL`, `LLM_ROUTE_IDEA_GENERATE_API_KEY_ENV`
  - `LLM_ROUTE_<TASK>_*` nadal ma najwyższy priorytet (nadpisuje profil)
  - resiliency: `LLM_ROUTE_IDEA_GENERATE_TIMEOUT_S`, `..._RETRIES`, `..._BREAKER_*`
  - telemetria/cost estimate: `LLM_PRICE_DEFAULT_INPUT_PER_1K`, `LLM_PRICE_DEFAULT_OUTPUT_PER_1K`
  - safety caps: `LLM_ROUTE_IDEA_GENERATE_MAX_TOKENS`, `..._MAX_COST_USD`, `LLM_DAILY_BUDGET_USD`, `LLM_TOKEN_BUDGETS`
  - OpenAI responses-only models: `LLM_OPENAI_RESPONSES_MODELS` (comma list)
  - audit log LLM calls: `LLM_AUDIT_LOG=1` (dodaje eventy do `audit_event`)
  - persystencja metryk/budżetu: `LLM_MEDIATOR_PERSIST_BACKEND=db` (fallback: `LLM_MEDIATOR_STATE_FILE`)
  - retention: `LLM_MEDIATOR_METRICS_RETENTION_DAYS`, `LLM_MEDIATOR_BUDGET_RETENTION_DAYS`
  - metryki runtime: `GET /llm/metrics` (operator-only)
- LLM Idea->DSL Compiler (legacy DSL, feature flag):
  - włącz: `IDEA_DSL_COMPILER_ENABLED=1`
  - działa tylko dla idei o statusie `feasible`/`ready_for_gate`
  - routing mediatora: `LLM_ROUTE_IDEA_COMPILE_DSL_*`
  - limity/retry: `IDEA_DSL_COMPILER_MAX_ATTEMPTS`, `IDEA_DSL_COMPILER_MAX_REPAIRS`
  - fallback awaryjny do template: `IDEA_DSL_COMPILER_FALLBACK_TEMPLATE=1`
  - wynik kompilacji zawiera `validation_report` (syntax/semantic/errors)
  - ręczne wymuszenie kompilacji:
    - API (operator-only): `POST /ideas/{idea_id}/compile-dsl`
    - CLI: `make idea-compile-dsl IDEA_COMPILE_ID=<UUID>`
- `make api` – uruchamia read‑only API (audit/metrics/idea embeddings).
  - Uwaga: API zawiera także endpointy operacyjne (`/ops/*`) oraz endpointy Idea Repository.
  - `API_PORT=8010 make api` – zmiana portu (domyślnie 8000).
  - `OPERATOR_TOKEN=sekret make api` – włącza guard operatora dla `/ops/*`.
  - Jeśli pojawia się warning `nice(5) failed`, uruchom `make api` poza sandboxem (to ograniczenie środowiska, nie projektu).
- `make run-dev` – spójne uruchomienie API+UI+worker (PORT API=8016, UI=5173, REDIS db=1).
- `make run-dev` ładuje `.env` i `.env.local` (zmienne przekazywane do API/worker/UI).
- Worker w dev uruchamia się jako `SimpleWorker` (bez forka) dla stabilności na macOS; jeśli potrzebujesz forka, ustaw `RQ_SIMPLE_WORKER=0`.
- `make run-dev` jest idempotentne: jeśli już działa, zwraca komunikat i exit 0.
- `make stop-dev` – zatrzymuje procesy uruchomione przez `make run-dev` i zwalnia porty API/UI.

### Pipeline (Godot/GDScript) – w przygotowaniu
- LLM generuje pelny skrypt GDScript (Godot 4.x).
- Walidacja: parse + load + krotki tick fizyki; bledy wracaja do LLM (limit prob).
- Preview render (Movie Maker) przed decyzja operatora.
- Render finalny -> QC -> publikacja -> metryki.
- Komendy i API dla nowego toru zostana dodane w ramach migracji.

### Manualny E2E (GUI-first) – checklista operatora
Docelowo caly przeplyw ma byc wykonywany krok po kroku z GUI (bez CLI). Na obecnym etapie:

1. Uruchom środowisko:
   - `make infra-up`
   - `make run-dev`
2. Otwórz UI (`http://localhost:5173`) i przejdź do widoku `Flow`.
3. Wygeneruj kandydatów (sekcja generatora / Idea Repository), następnie zweryfikuj że kandydaci są `feasible`.
4. W `Idea Gate` wybierz dokładnie jednego kandydata (`picked`) i zapisz decyzję.
5. Uruchom render (obecnie legacy/manual ops zależnie od etapu migracji) i poczekaj aż animacja pojawi się na liście `Animations`.
6. W `Animations` wybierz animację i sprawdź:
   - podgląd wideo,
   - artefakty,
   - status renderu i stage.
7. W panelu szczegółów animacji zapisz decyzję `QC` (`accepted` / `rejected` / `regenerate`) wraz z notatką, jeśli potrzebna.
8. Jeśli `QC=accepted`, zapisz `Publish Record (manual)` dla platformy (`youtube`/`tiktok`) i ustaw status (najczęściej `manual_confirmed` albo `published`).
9. Zweryfikuj w UI:
   - zmianę statusu animacji (`published`) i etapu (`metrics`) po publikacji,
   - wpisy w `Audit log` (`qc_decision`, `publish_record`).
10. Jeśli coś nie działa, zanotuj błąd i dodaj podpunkt ryzyka/korekty do `TODO.md` (zgodnie z `AGENTS.md`).

Uwagi:
- Na tym etapie automatyzacje i pełny tor Godot (`compile_gdscript -> validate -> preview -> final_render`) są rozwijane krok po kroku.
- Dla etapu Godot można lokalnie weryfikować runner CLI przez `make godot-verify-cli`, `make godot-preview`, `make godot-render`.

### Godot CLI (lokalna weryfikacja)
Do testu flag Godota (headless + write-movie):
```bash
make godot-verify-cli GODOT_SCRIPT=/abs/path/to/script.gd
```
Domyslnie skrypty/targety probuja uzyc lokalnej binarki z `./.tools/godot/current/Godot.app/Contents/MacOS/Godot` (instalowanej przez `make godot-install`), a dopiero potem `godot` z `PATH`.
`GODOT_BIN` ustawiaj tylko wtedy, gdy chcesz jawnie nadpisac domyslna sciezke.
Podglad/render (Movie Maker) wspiera tylko `.ogv/.avi`, ale `scripts/godot-run.py` automatycznie konwertuje do `.mp4` przez FFmpeg:
```bash
make godot-preview GODOT_SCRIPT=/abs/path/to/script.gd GODOT_PREVIEW_OUT=out/godot/preview.mp4
make godot-render GODOT_SCRIPT=/abs/path/to/script.gd GODOT_OUT=out/godot/final.mp4
```
Tryb preview (domyslny): krotki klip 2s @ 12 FPS, skala 0.5, zapis do `out/godot/preview.mp4`.
Ustawienia (opcjonalne): `GODOT_PREVIEW_SECONDS`, `GODOT_PREVIEW_FPS`, `GODOT_PREVIEW_SCALE`, `GODOT_PREVIEW_OUT`.

### Operacje (API) – przykłady curl (legacy DSL)
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

### Pipeline (legacy DSL) – minimalny flow
1. Uruchom infra: `make infra-up`
2. Zainstaluj deps (jeśli zmiany w `pyproject.toml`): `make deps-py-uv`
3. Start workera: `make worker`
4. Enqueue: `make enqueue`
5. Status: `make job-status` lub `make job-summary`

### Zmienne środowiskowe (.env)
Uwaga: ponizsza lista dotyczy glownie legacy sciezki DSL; nowy tor Godot/GDScript doda wlasne zmienne.
- `DATABASE_URL` – połączenie do Postgresa.
- `REDIS_URL` – połączenie do Redis (RQ).
- `RQ_JOB_TIMEOUT` / `RQ_RENDER_TIMEOUT` – timeouty jobów w sekundach.
- `FFMPEG_TIMEOUT_S` – timeout ffmpeg w rendererze.
- `IDEA_GATE_COUNT` – liczba propozycji losowanych w Idea Gate.
- `DEV_MANUAL_FLOW` – tryb manualny (bez automatycznych akcji w Idea Gate), `1` aby włączyć.
- `OPENAI_API_KEY` – klucz do generatora pomysłów (opcjonalny).
- `OPENAI_MODEL` – model OpenAI dla generatora pomysłów (np. `gpt-4o-mini`).
- `OPENAI_BASE_URL` – endpoint API (domyślnie `https://api.openai.com/v1`).
- `OPENAI_TEMPERATURE` – temperatura generacji (domyślnie `0.7`).
- `OPENAI_MAX_OUTPUT_TOKENS` – limit tokenów odpowiedzi (domyślnie `800`).
- `ARTIFACTS_BASE_DIR` – katalog bazowy dla serwowania artefaktów (domyślnie `out`).
- `OPERATOR_TOKEN` – prosty token operatora dla endpointów `/ops/*` (nagłówek `X-Operator-Token`).
- `ALLOW_OPS_WITHOUT_TOKEN` – jeśli `1`, pozwala na `/ops/*` bez tokena (domyślnie `0`).
- `CLEANUP_OLDER_MIN` – próg minut dla auto-cleanup `running` przy starcie `make run-dev` (domyślnie 30).
- `LLM_ROUTE_<TASK>_PROVIDERS` / `LLM_ROUTE_<TASK>_MODELS` – lista providerów/modeli w kolejności fallbacku (np. `gemini,openai` / `gemini-2.5-pro,gpt-5.2-codex`).
- `LLM_ROUTE_<TASK>_API_KEY_ENVS` / `LLM_ROUTE_<TASK>_API_KEY_HEADERS` – opcjonalne listy kluczy/nagłówków dla powyższych providerów.
- `LLM_TOKEN_BUDGETS` – JSON limitów tokenów per model lub grupa modeli (sumuje prompt+completion, reset dzienny). Przykład:
  ```
  {"models":{"openai:gpt-5.1-codex-mini":2000000},"groups":{"codex":{"limit":2000000,"members":["openai:gpt-5.1-codex-mini","openai:gpt-5.2-codex"]}}}
  ```

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
- Godot i FFmpeg uruchamiane natywnie na macOS dla stabilnosci i dostepnosci bibliotek.
- Zmiany wersji narzędzi powinny być wykonywane przez aktualizację `Brewfile` i lockfile.
- W razie zawieszeń renderu sprawdź `make job-summary` i użyj `make job-cleanup`.
  - Jeśli render wisi tylko w workerze, upewnij się, że używasz najnowszej wersji (ffmpeg z `-nostdin` + absolutne ścieżki).
