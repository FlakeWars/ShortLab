# ShortLab

ShortLab to lokalny pipeline do codziennego generowania i publikacji krótkich animacji 2D (Shorts), z panelem review, półautomatyczną publikacją i metrykami dla YouTube/TikTok. Nowy kierunek zaklada Godot 4.x + pelny GDScript generowany przez LLM (deterministycznosc nie jest celem nadrzednym).

## Zakres MVP
- Generacja jednego pomyslu (lub wybór z `later`) -> skrypt GDScript -> walidacja/naprawa -> estimate_duration -> preview -> intent_check -> final render -> intro tekst + audio -> QC -> publikacja -> metryki.
- Render 2D w Godot 4.x (Movie Maker) + opcjonalny FFmpeg.
- Lokalna infrastruktura: Postgres, Redis, MinIO (Docker Compose).
- Panel review: React + Vite.

## Stan implementacji (2026-03-24)
- Dziala legacy sciezka DSL: enqueue -> generate_dsl -> render -> artefakty.
- Dziala Idea Repository/Idea Gate + embeddings.
- Dziala mediator LLM z routingiem i persystencja metryk/budzetu w DB.
- Dziala manualny flow Godot E2E po API: `idea_generate -> idea_gate -> compile -> validate -> estimate_duration -> preview -> intent_check -> final_render`.
- Nowy kierunek: operator-first `single-video cadence` (1 film co 1-2 dni) z uproszczonym flow UI.
- Dziala `Insights summary` (24h/72h/7d/14d) z rekomendacją i top content 14d w widoku Plan.
- Dziala monitoring `intro_translate_14d` w Insights (translated/fallback/disabled + fallback rate z audit eventów intro overlay).
- W Insights fallback rate tłumaczeń intro powyżej 10% jest oznaczany alertem operatorskim.
- Dziala `Publish connector preflight` (`/publish/connectors/status`) i panel gotowości konektorów w `Publish Record (manual)`.
- Dziala endpoint statusowy `GET /publish/readiness-summary` (operator-only) oparty o latest raport readiness gate.
- Dziala panel `Publish readiness gate` w `Plan / Calendar` (status `overall` + komponenty gate).
- Dziala filtrowanie historii publikacji w `Plan / Calendar` (`platforma`, `status`, `date from/to`).
- Dziala walidacja timezone (IANA) w ustawieniach planera po stronie UI (inline error + blokada zapisu).
- Dzialaja CTA z panelu statusu (`Today/System status`) do docelowych widoków (`Flow`, `Repositories`).
- Dziala mapa przyjaznych slugów i tytułów widoków (`view=today|flow|insights|repositories|settings`) z breadcrumbem aktywnego ekranu.
- Dziala jasny podział list animacji: `Flow` pokazuje mini-preview, a `Repositories` pełną listę diagnostyczną.
- W `single-video` widok `Flow` domyślnie ukrywa panele zaawansowane (`Logi operacyjne`, `Operations`) i odsłania je jednym przełącznikiem.
- App-shell (`Home`, `Plan`, `Flow`) ma spójny copy po polsku dla głównych nagłówków i CTA.
- Główne sekcje `Repositories` (nagłówki/CTA/filtry) również używają copy po polsku.
- `audio_mix` ma domyślną normalizację głośności (`loudnorm`) i clipping guard (`alimiter`) z parametrami sterowanymi w API/UI.
- `Audio mix` ma profile presetów (`balanced`, `speech`, `music`, `sfx_heavy`) do szybkiego ustawiania LUFS/TP i gain.
- `intent_check` ma presety kalibracyjne (`balanced`, `fast_hook`, `gradual_reveal`, `loop_pattern`) do szybkiego ustawiania `threshold/hold/tail` w manual run.
- Dziala endpoint `POST /ops/publish/readiness-refresh` (operator-only), który uruchamia checki gate i odświeża summary.
- Panel statusu ma SLO/fallback: polling 15s, timeout requestu 8s, stale-hint po 60s oraz czytelny komunikat o mismatch API/UI gdy `/system/status` jest niedostępny.
- `/system/status` wspiera lekki cache TTL (`SYSTEM_STATUS_CACHE_TTL_S`, domyślnie `5s`) i zwraca `response_time_ms` + metadane cache.
- Widok animacji ma polling co 20s w `Flow`/`Repositories` oraz wyraźny przycisk `Odśwież` obok filtrów.
- Decyzja integracyjna: MCP dla social platform używamy jako warstwę wspierającą (insights/research), a krytyczny publish/metrics pozostaje na oficjalnych API YouTube/TikTok.
- Plan wykonawczy: `.ai/operator-flow-v2.md`.

## Operator-first flow (single-video cadence)
- Cel: operator ma wykonywać jeden, czytelny flow bez przeskakiwania między wieloma panelami.
- Zasada: domyślnie pracujemy na jednym pomyśle i jednym aktywnym filmie.
- Kolejność: `Pomysł -> Animacja -> Intro/Audio -> QC -> Publish -> Metrics`.
- W trybie `single-video` panel Flow prowadzi jednym aktywnym krokiem (następne kroki odblokowują się po sukcesie poprzednich).
- Runtime: domyślnie `60s` (jeden format dla wszystkich platform), z opcjonalnym override per film.
- Język intro: domyślnie `EN`.
- Język aplikacji i pomysłów: `PL`; język napisów/overlay w filmie: `EN`.
- Intro overlay w EN używa tłumaczenia LLM (`intro_translate`) z fallbackiem do sanitizacji (mapowanie typowych prefiksów PL + transliteracja znaków).
- Nietrafione pomysły:
  - `later`: do ponownego użycia.
  - `trash`: natychmiastowy hard-delete.
  - `later` cleanup: kandydaty starsze niż `OPERATOR_LATER_MAX_AGE_DAYS` można czyścić akcją operatora (`cleanup later`).

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
- `make mcp-publish-audit` – formalny audyt MCP dla trialu publish/analytics (raport JSON/MD do `out/reports`).
- `make publish-oauth-smoke` – smoke test OAuth refresh dla YouTube/TikTok (offline/online, raport JSON/MD do `out/reports`).
- `make mcp-compliance-check` – formalna walidacja checklisty compliance przed trialem MCP (raport JSON/MD + gate).
- `make publish-readiness-check` – uruchamia pełny gate (MCP audit + compliance + OAuth smoke) z domyślnymi progami bezpieczeństwa.
- `make publish-readiness-summary` – agreguje latest raporty do jednego statusu gotowości (`out/reports/publish-readiness-summary-latest.*`).
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
    - `intro_translate` -> `structured`
  - profile map: `LLM_TASK_PROFILE_<TASK>=creative|analytical|structured`
  - profile defaults: `LLM_PROFILE_<PROFILE>_*` (provider/model/timeout/retries/limits)
  - `LLM_ROUTE_IDEA_GENERATE_PROVIDER=openai|openrouter|groq|litellm`
  - `LLM_ROUTE_IDEA_GENERATE_MODEL=<model>`
  - opcjonalnie `LLM_ROUTE_IDEA_GENERATE_BASE_URL`, `LLM_ROUTE_IDEA_GENERATE_API_KEY_ENV`
  - `LLM_ROUTE_<TASK>_*` nadal ma najwyższy priorytet (nadpisuje profil)
  - resiliency: `LLM_ROUTE_IDEA_GENERATE_TIMEOUT_S`, `..._RETRIES`, `..._BREAKER_*`
  - telemetria/cost estimate: `LLM_PRICE_DEFAULT_INPUT_PER_1K`, `LLM_PRICE_DEFAULT_OUTPUT_PER_1K`
  - safety caps: `LLM_ROUTE_IDEA_GENERATE_MAX_TOKENS`, `..._MAX_COST_USD`, `LLM_DAILY_BUDGET_USD`, `LLM_TOKEN_BUDGETS`
  - uproszczony routing dla iteracyjnego toru `idea + GDScript`: `LLM_ITERATIVE_ROUTE_TASKS`, `LLM_ITERATIVE_ROUTE_MODELS`, `LLM_ITERATIVE_MODEL_TOKEN_LIMITS`
  - gdy preferowany model przekroczy limit tokenów, mediator przechodzi do kolejnego modelu z fallbacku (zamiast twardego fail taska)
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
- `make run-dev-preflight` – uruchamia `run-dev` i od razu wykonuje smoke `godot-smoke-preview-render`.
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
3. Wygeneruj kandydatów w `Idea Generator`; jeśli coś zostało pominięte, sprawdź sekcję `Powody pominięcia (skip)`.
4. W `Idea Gate` wybierz dokładnie jednego kandydata (`picked`) i zapisz decyzję.
5. W `Manual Flow -> Godot Manual Run` wykonaj kroki:
   - `Compile GDScript`
   - `Validate`
   - `Estimate duration` (opcjonalnie kliknij `Use recommendation`)
   - `Preview`
   - `Intent check` (gate: pass/blocked + rekomendowany czas symulacji i speed factor)
   - `Final render`
   - `Intro overlay` (krótki hook tekstowy na początku wideo)
   - `Audio mix` (SFX i/lub muzyka tła)
   i poczekaj aż animacja pojawi się na liście `Animations`.
6. W `Animations` wybierz animację i sprawdź:
   - podgląd wideo,
   - artefakty,
   - status renderu i stage.
7. W panelu szczegółów animacji zapisz decyzję `QC` (`accepted` / `rejected` / `regenerate`) wraz z notatką, jeśli potrzebna.
   - Dla `accepted` wymagane jest potwierdzenie trzech flag jakości: `idea intent`, `intro readability`, `audio quality`.
8. Jeśli `QC=accepted`, w sekcji `Publish Record (manual)` sprawdź `Connector preflight`, a następnie zapisz publikację dla platformy (`youtube`/`tiktok`) ze statusem (najczęściej `manual_confirmed` albo `published`).
9. Zweryfikuj w UI:
   - zmianę statusu animacji (`published`) i etapu (`metrics`) po publikacji,
   - wpisy w `Audit log` (`qc_decision`, `publish_record`).
10. Jeśli coś nie działa, zanotuj błąd i dodaj podpunkt ryzyka/korekty do `TODO.md` (zgodnie z `AGENTS.md`).

Uwagi:
- Na tym etapie automatyzacje są ograniczone (manual-first), ale tor Godot w GUI obejmuje już `compile_gdscript -> validate -> estimate_duration -> preview -> intent_check -> final_render -> intro_overlay -> audio_mix`.
- Dla etapu Godot można lokalnie weryfikować runner CLI przez `make godot-verify-cli`, `make godot-preview`, `make godot-render`, `make godot-smoke-preview-render`.

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
- `OPERATOR_SINGLE_VIDEO_MODE` – tryb operator-first (domyślnie `1`): generator i Idea Gate pracują na 1 propozycji, a nawigacja preferuje `Today -> Flow -> Insights`.
- `OPERATOR_TARGET_RUNTIME_S` – docelowy runtime filmu (domyślnie `60`), używany jako wartość bazowa do skalowania finalnego czasu.
- `OPERATOR_INTRO_LANGUAGE` – domyślny język intro overlay (domyślnie `en`).
- `INTRO_EN_TRANSLATE_ENABLED` – włącza/wyłącza próbę tłumaczenia EN dla intro overlay (`1` domyślnie, `0` = tylko sanitizacja fallback).
- `LLM_TASK_PROFILE_INTRO_TRANSLATE` – profil routingu taska tłumaczenia intro (`structured` domyślnie).
- `LLM_ROUTE_INTRO_TRANSLATE_PROVIDER` / `LLM_ROUTE_INTRO_TRANSLATE_MODEL` – jawny routing modelu dla tłumaczenia intro (niezależnie od innych tasków LLM).
- `OPERATOR_LATER_MAX_AGE_DAYS` – domyślny limit wieku kandydatów `later` dla cleanup (domyślnie `30`).
- `MCP_REGISTRY_BASE` – opcjonalny endpoint registry dla audytu MCP (domyślnie `https://registry.modelcontextprotocol.io`).
- `MCP_AUDIT_FAIL_ON_RISK_LEVEL` – opcjonalny próg fail-fast dla `make mcp-publish-audit` (`none|high|medium`).
- `OAUTH_SMOKE_ONLINE` – dla `make publish-oauth-smoke`: `1` wykonuje realny refresh request do providerów.
- `OAUTH_SMOKE_REQUIRE` – polityka fail-fast dla `make publish-oauth-smoke` (`none|passed_if_configured|passed_all`).
- `MCP_COMPLIANCE_REQUIRE` – polityka fail-fast dla `make mcp-compliance-check` (`strict|none`).
- `PUBLISH_READINESS_MAX_ALLOWED_RISK` – próg ryzyka dla `make publish-readiness-summary` (`low|medium|high`).
- `PUBLISH_READINESS_REQUIRE_PASS` – jeśli `1`, `make publish-readiness-summary` zwraca błąd gdy `overall_pass=false`.
- `PUBLISH_READINESS_SUMMARY_FILE` – ścieżka latest summary używana przez API `/publish/readiness-summary` (domyślnie `out/reports/publish-readiness-summary-latest.json`).
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` (lub `YOUTUBE_ACCESS_TOKEN`) – dane konektora YouTube (status `ready=api`).
- `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` / `TIKTOK_REFRESH_TOKEN` (lub `TIKTOK_ACCESS_TOKEN`) – dane konektora TikTok (status `ready=api`).
- `OPENAI_API_KEY` – klucz do generatora pomysłów (opcjonalny).
- `OPENAI_MODEL` – model OpenAI dla generatora pomysłów (np. `gpt-4o-mini`).
- `OPENAI_BASE_URL` – endpoint API (domyślnie `https://api.openai.com/v1`).
- `OPENAI_TEMPERATURE` – temperatura generacji (domyślnie `0.7`).
- `OPENAI_MAX_OUTPUT_TOKENS` – limit tokenów odpowiedzi (domyślnie `800`).
- `ARTIFACTS_BASE_DIR` – katalog bazowy dla serwowania artefaktów (domyślnie `out`).
- `OPERATOR_TOKEN` – prosty token operatora dla endpointów `/ops/*` (nagłówek `X-Operator-Token`).
- `ALLOW_OPS_WITHOUT_TOKEN` – jeśli `1`, pozwala na `/ops/*` bez tokena (domyślnie `0`).
- `CLEANUP_OLDER_MIN` – próg minut dla auto-cleanup `running` przy starcie `make run-dev` (domyślnie 30).
- `RUN_DEV_HEALTHCHECK_URL` – URL healthcheck używany przez `scripts/run-dev.sh` po starcie (domyślnie `http://localhost:${API_PORT}/health`).
- `RUN_DEV_HEALTHCHECK_RETRIES` – liczba prób healthcheck po starcie `run-dev` (domyślnie `30`).
- `RUN_DEV_HEALTHCHECK_INTERVAL_S` – odstęp między próbami healthcheck (domyślnie `1` sekunda).
- `LLM_ROUTE_<TASK>_PROVIDERS` / `LLM_ROUTE_<TASK>_MODELS` – lista providerów/modeli w kolejności fallbacku (np. `gemini,openai` / `gemini-2.5-pro,gpt-5.2-codex`).
- `LLM_ROUTE_<TASK>_API_KEY_ENVS` / `LLM_ROUTE_<TASK>_API_KEY_HEADERS` – opcjonalne listy kluczy/nagłówków dla powyższych providerów.
- `LLM_TOKEN_BUDGETS` – JSON limitów tokenów per model lub grupa modeli (sumuje prompt+completion, reset dzienny). Dla iteracyjnego toru `idea + GDScript` można zostawić tu tylko inne modele (np. Gemini), bo limity iteracyjne mają dedykowane zmienne poniżej. Przykład:
  ```
  {"models":{"openai:gpt-5.1-codex-mini":2000000},"groups":{"codex":{"limit":2000000,"members":["openai:gpt-5.1-codex-mini","openai:gpt-5.2-codex"]}}}
  ```
- `LLM_ITERATIVE_ROUTE_TASKS` – taski objęte uproszczonym routingiem iteracyjnym (domyślnie: `idea_generate,gdscript_generate,gdscript_repair`).
- `LLM_ITERATIVE_ROUTE_MODELS` – lista modeli (provider:model) dla tych tasków w kolejności preferencji/fallbacku, np. `openai:gpt-5.2-codex,openai:gpt-5.1-codex-mini`. Dla tasków z `LLM_ITERATIVE_ROUTE_TASKS` mediator użyje tej listy zamiast pojedynczego `LLM_ROUTE_<TASK>_MODEL`.
- `LLM_ITERATIVE_MODEL_TOKEN_LIMITS` – JSON limitów tokenów dla modeli z powyższej listy, np. `{"openai:gpt-5.2-codex":200000,"openai:gpt-5.1-codex-mini":2000000}`. Po wyczerpaniu limitu mediator automatycznie przechodzi do kolejnego modelu z fallbacku.
- `LLM_TOKEN_BUDGET_RESERVATION_MARGIN` – konserwatywny margines rezerwacji tokenów (prompt upper-bound) używany przed requestem, żeby nie uruchamiać modelu gdy request mógłby przekroczyć limit. Wyższa wartość = twardsza ochrona, ale wcześniejsze przełączanie na fallback.

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
