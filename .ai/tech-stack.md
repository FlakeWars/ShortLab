# Proponowany stos technologiczny (MVP)

Poniżej propozycja spójnego stosu dla lokalnego, deterministycznego pipeline’u z panelem review i półautomatyczną publikacją. Dobór skupia się na: deterministyczności, prostocie uruchomienia lokalnego, łatwym debugowaniu oraz możliwości rozszerzania.

## 1. Języki i runtime
- **Python 3.12**: główny język backendu i workerów (szybki development, dobre biblioteki do AI, pipeline i integracji API).
- **TypeScript**: panel review (front + ewentualne typy kontraktów API).
- **SQL**: definicja schematu danych i analiz (PostgreSQL).

## 2. Backend API i panel review
- **FastAPI**: szybki backend HTTP/JSON, łatwe walidacje modeli, dokumentacja OpenAPI.
- **React + Vite + TypeScript**: panel operacyjny systemu (pipeline, Idea Gate, QC, metryki).
- **TanStack Query**: cache danych, odświeżanie statusów jobów (polling).
- **TanStack Table**: listy animacji/jobów z filtrowaniem.
- **Wykresy**: **ECharts** lub **Recharts** do metryk i trendów.
- **Tailwind CSS**: szybkie i spójne budowanie UI w MVP.
- **shadcn/ui**: gotowe, dostępne komponenty (design primitives) budowane na Tailwind.
- **Auth**: session-based auth z hashem (Argon2), tylko dla operatora; opcjonalnie podstawowy 2FA (TOTP).

## 3. Kolejki zadań i workerzy
- **Redis**: kolejka zadań i krótkotrwały cache.
- **RQ** lub **Celery**:
  - RQ: prostota i szybkość w MVP.
  - Celery: gdy pojawi się potrzeba złożonych workflow i retry.
- **Scheduler**: **APScheduler** (lokalny harmonogram uruchomień dziennych).

## 4. DSL, wersjonowanie i deterministyczność
- **DSL w YAML/JSON** (z wersją schematu): łatwe diffy i walidacja.
- **Walidacja schematu**: `pydantic` + `jsonschema`.
- **Wersjonowanie DSL**: pole `dsl_version` oraz migratory "upgrader" w kodzie.
- **DSL Capability Verifier** (MVP): oddzielny etap `Idea -> feasible?` (TAK/NIE + `dsl_gaps`) przed kompilacja.
- **LLM DSL Compiler** (MVP): etap `Idea -> DSL` tylko dla idei wykonalnych, z torem `generate -> validate -> repair/retry -> fallback`.
- **Raportowanie luk DSL**: `dsl_gaps` zapisywane do backlogu/audytu jako input do rozwoju DSL.

## 4a. Embedding i podobieństwo (Idea Gate / deduplikacja)
- **scikit-learn (HashingVectorizer)**: lokalne embeddings (CPU) bez pobierania modeli.
- **Cosine similarity**: podstawowa miara podobieństwa.
- **Fallback offline**: hash-embedding, gdy wektorizer niedostępny.

## 5. Silnik renderingu 2D
- **MVP-first**: **Python + Skia-Python** lub **Cairo** jako renderer:
  - Szybszy start i niższy koszt utrzymania.
  - Wystarczające do 14-dniowego eksperymentu, jeśli deterministyczność jest stabilna.
- **Docelowo**: **Rust + Skia** (np. `skia-safe`) jako osobny serwis/CLI renderer:
  - Silniejsza deterministyczność (kontrola RNG, stabilność float).
  - Lepsza wydajność dla większej skali.
- **FFmpeg**: spójna kompresja wideo i kontrola parametrów exportu.

## 6. Dane i przechowywanie
- **PostgreSQL**: metadane, statusy pipeline, QC, audit log, tagi, metryki.
- **Lokalny storage** jako domyślny wybór MVP (wideo renderów, preview, artefakty).
- **MinIO (S3 compatible)** jako opcja przy wzroście wolumenu danych lub migracji do chmury.
- **Alembic**: migracje bazy danych.

## 7. Integracje publikacji i metryk
- **YouTube Data API v3**: upload + metryki (daily pull).
- **TikTok**:
  - Jeśli API niedostępne: flow półmanualny z potwierdzeniem publikacji.
  - Gdy możliwe: TikTok Content Posting API (wymaga weryfikacji).
- **Worker integracyjny**: osobne zadania "publish" i "metrics_pull" z retry i logami.

## 8. QC, audit i wersjonowanie design systemu
- **Checklisty QC** jako słowniki w DB + wersjonowanie.
- **Audit log** w DB: user_id, event_type, payload, timestamp.
- **Design System** jako osobny pakiet JSON/TS + wersja przypisana w metadanych renderu.

## 9. Analiza KPI i eksport
- **SQL views** do obliczeń rolling 14 dni i agregacji 72h/7d.
- **Eksport** do CSV/Parquet (np. `pandas`).

## 10. Observability i diagnostyka
- **Strukturalne logi**: `structlog` lub `loguru`.
- **Dashboard minimalny**: endpoint zdrowia + status jobów.
- **Tracing** (opcjonalnie, po MVP): OpenTelemetry, jeśli pipeline się rozrośnie.

## 10.1. UI – zakres operacyjny (MVP)
- **Dashboard**: status pipeline + ostatnie joby (queued/running/failed/succeeded).
- **Animacje**: lista animacji + metadane + statusy.
- **Render**: podgląd wideo + metryki renderu + DSL/Design System.
- **Idea Gate**: propozycje + wybór + similarity.
- **QC**: decyzje i checklisty.
- **Audit log**: historia zdarzeń i filtr po typie.

## 11. Testy i jakość
- **Pytest**: testy pipeline, DSL i deterministyczności renderu (golden tests).
- **Playwright**: testy smoke UI panelu review.
- **Pre-commit**: format/lint (ruff + black).

## 12. Pakiety i uruchamianie
- **Docker Compose**: lokalne uruchamianie (Postgres, Redis, MinIO).
- **uv** lub **poetry**: zarządzanie zależnościami Python.
- **Makefile**: wygodne taski (build, render, run, migrate).

### Uwaga: macOS (Apple Silicon, M2) i odporność na zmiany sprzętowe
Jeśli głównym celem jest stabilność środowiska na macOS ARM64 oraz dostępność bibliotek (Skia/Cairo/FFmpeg), pełna konteneryzacja może nie pomóc, bo Docker działa w VM z Linuksem i nie zapewnia macOS-owych zależności. Zalecane podejście:
- **Usługi infrastrukturalne w Compose** (Postgres/Redis/MinIO).
- **Renderer i FFmpeg natywnie na macOS** z twardo przypiętymi wersjami.
- **Pinning zależności**: `pyproject` + lock (`uv`/`poetry`), opcjonalnie `constraints.txt`.
- **Bootstrap środowiska**: `Brewfile` + `scripts/setup-macos.sh` dla powtarzalnego setupu.

## Rekomendowany minimalny zestaw (start MVP)
1. Python + FastAPI + RQ + Redis
2. Postgres + Alembic
3. Renderer Python+Skia-Python/Cairo + FFmpeg
4. React + Vite panel review
5. Lokalny storage dla wideo

## Plan migracji z MVP do wersji docelowej
1. **Etap 0 (MVP)**: Pythonowy renderer, lokalny storage, podstawowa observability.
2. **Etap 1 (Stabilizacja)**:
   - Ustalić deterministyczność i dodać golden tests renderu.
   - Zdefiniować tolerancje pikselowe i wersjonowanie renderera.
3. **Etap 2 (Renderer docelowy)**:
   - Wydzielić renderer jako osobny CLI/serwis w Rust+Skia.
   - Utrzymać kontrakt wejścia/wyjścia zgodny z MVP (DSL + metadane).
4. **Etap 3 (Storage i skala)**:
   - Przenieść artefakty do MinIO/S3.
   - Dodać polityki retencji i lifecycle dla odrzuconych renderów.
5. **Etap 4 (Operacyjność)**:
   - Dodać tracing (OpenTelemetry), jeśli rośnie liczba jobów.
   - Rozważyć Celery, gdy workflow wymaga złożonych retry i zależności.

## Uzasadnienie wyboru
- **Szybkość iteracji**: Python i FastAPI minimalizują koszt zmian i eksperymentów.
- **MVP bez nadmiernej złożoności**: renderer w Pythonie na start, z jasną ścieżką do Rust+Skia.
- **Deterministyczność**: kontrola RNG + metadane renderu; możliwość podmiany renderera bez zmiany pipeline.
- **Czytelny pipeline**: job queue + statusy w DB = proste debugowanie.
- **Skalowalność w przyszłości**: łatwa migracja do chmury (S3, K8s) bez przebudowy architektury.

## Uwagi dot. bezpieczeństwa (MVP)
- **Przechowywanie kluczy**: `.env`/vault lokalny + ograniczone uprawnienia plików.
- **Auth**: session-based + Argon2, logowanie zdarzeń i nieudanych prób.
- **Panel**: podstawowy rate limiting i blokada publikacji bez konfiguracji kluczy.
# Generator pomysłów (moduł)
- **Provider**: OpenAI API / lokalny LLM (opcjonalnie) jako generator pomysłów.
- **Fallback**: statyczny plik `.ai/ideas.md` + zapis wygenerowanych pomysłów do DB.
- **Embedding**: docelowo embeddingi modelowe (np. OpenAI) zamiast hash‑embeddingu.

# Embedding Service (moduł)
- **Provider**: OpenAI embeddings / lokalny model (opcjonalnie).
- **Cache + retry + rate limit**: ochrona kosztów i stabilność.
- **Fallback**: hash‑embedding w trybie offline.
