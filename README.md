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
4. Uruchom infrastrukturę:
   - Docker Desktop zainstaluj manualnie (bootstrap pomija cask)
   - `make infra-up`
5. Uruchom API/worker/UI (gdy kod będzie gotowy):
   - `make api`
   - `make worker`
   - `make ui`

### Pipeline (MVP) – komendy operacyjne
- `make worker` – startuje workera RQ.
- `make enqueue` – wrzuca minimalny job (generacja DSL -> render).
  - `IDEA_GATE_ENABLED=1 make enqueue` – włącza Idea Gate w pipeline.
- `make job-status` – pokazuje ostatnie joby.
- `make job-summary` – podsumowanie statusów jobów.
- `make job-cleanup OLDER_MIN=30` – oznacza stare joby `running` jako `failed`.
- `make idea-gate` – proponuje pomysły i wybór (Idea Gate).
  - Używa `.ai/ideas.md`, wybór przez `IDEA_GATE_SELECT` lub `IDEA_GATE_AUTO=1`.

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
- `IDEA_GATE_COUNT` – liczba propozycji w Idea Gate.
- `IDEA_GATE_THRESHOLD` – próg podobieństwa (oznaczanie „too_similar”).
- `IDEA_GATE_AUTO` – jeśli `1`, wybiera automatycznie najniższe podobieństwo.
- `IDEA_GATE_SELECT` – ręczny wybór (1-based indeks z listy).

## Makefile
Dostępne cele:
- `make help` – lista targetów.
- `make doctor` – szybka diagnostyka środowiska.
- `make infra-up` / `infra-down` – Postgres/Redis/MinIO.

## Dokumentacja
- `/.ai/prd.md` – wymagania produktu.
- `/.ai/tech-stack.md` – stos technologiczny.
- `/.ai/bootstrap.md` – plan bootstrapu macOS.
- `/versions.env` – przypięte wersje narzędzi i usług.

## Uwagi
- Renderer i FFmpeg uruchamiane natywnie na macOS dla stabilności i dostępności bibliotek.
- Zmiany wersji narzędzi powinny być wykonywane przez aktualizację `Brewfile` i lockfile.
- W razie zawieszeń renderu sprawdź `make job-summary` i użyj `make job-cleanup`.
  - Jeśli render wisi tylko w workerze, upewnij się, że używasz najnowszej wersji (ffmpeg z `-nostdin` + absolutne ścieżki).
