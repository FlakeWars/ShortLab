# Stos technologiczny (MVP) - stan aktualny

Dokument opisuje stack faktycznie używany w repozytorium oraz elementy planowane. Dobór skupia się na: szybkim uzyskaniu dzialajacej animacji, prostocie uruchomienia lokalnego, latwym debugowaniu oraz mozliwosci rozszerzania.

## 1. Języki i runtime
- **Python 3.12**: główny język backendu i workerów (szybki development, dobre biblioteki do AI, pipeline i integracji API).
- **TypeScript**: panel review (front + ewentualne typy kontraktów API).
- **SQL**: definicja schematu danych i analiz (PostgreSQL).

## 2. Backend API i panel review
- **FastAPI**: szybki backend HTTP/JSON, łatwe walidacje modeli, dokumentacja OpenAPI.
- **React + Vite + TypeScript**: panel operacyjny systemu (pipeline, Idea Gate, QC, metryki).
- **Tailwind CSS**: szybkie i spójne budowanie UI w MVP.
- **shadcn/ui**: gotowe, dostępne komponenty (design primitives) budowane na Tailwind.
- **Auth (aktualnie)**: brak pełnego loginu sesyjnego; endpointy operacyjne chronione tokenem operatora.
- **Auth (plan)**: session-based auth z hashem (Argon2), tylko dla operatora; opcjonalnie podstawowy 2FA (TOTP).
- **Planowane po MVP**: TanStack Query/Table oraz biblioteka wykresów po rozbudowie UI.

## 3. Kolejki zadań i workerzy
- **Redis**: kolejka zadań i krótkotrwały cache.
- **RQ** lub **Celery**:
  - RQ: prostota i szybkość w MVP.
  - Celery: gdy pojawi się potrzeba złożonych workflow i retry.
- **Scheduler**: **APScheduler** (lokalny harmonogram uruchomień dziennych).

## 4. Skrypt GDScript, kontrakt i walidacja
- **GDScript (Godot 4.x)**: pelny skrypt generowany przez LLM (bez template'ow animacji).
- **Kontrakt skryptu**: ograniczona pula node/shape + limit czasu/obiektow; brak IO/sieci poza workspace.
- **Walidacja skryptu**: parse + load + krotki tick fizyki (smoke test) przed renderem.
- **Petla naprawy**: precyzyjny raport bledow -> retry LLM (limit prob).
- **Wersjonowanie**: wersja Godot i kontraktu skryptu zapisywane w metadanych renderu.

## 4a. Embedding i podobieństwo (Idea Gate / deduplikacja)
- **scikit-learn (HashingVectorizer)**: lokalne embeddings (CPU) bez pobierania modeli.
- **Cosine similarity**: podstawowa miara podobieństwa.
- **Fallback offline**: hash-embedding, gdy wektorizer niedostępny.

## 5. Silnik renderingu 2D
- **Godot 4.x**: silnik renderu i fizyki 2D.
- **Movie Maker**: render offline/CLI (preview + final).
- **FFmpeg**: opcjonalna kompresja i postprocessing wideo.
- **Legacy**: Python + Skia/Cairo pozostaja w repo jako stary tor, ale nie sa juz kierunkiem docelowym.

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
- **Render**: podglad wideo + metryki renderu + hash skryptu/Godot/Design System.
- **Idea Gate**: propozycje + wybór + similarity.
- **QC**: backend flow jest dostępny, osobny panel UI jest w backlogu.
- **Audit log**: historia zdarzeń i filtr po typie.
- **Ops**: enqueue/rerun/cleanup z guardem operatora.

## 11. Testy i jakość
- **Pytest**: testy pipeline, walidacji skryptu i stabilnosci renderu (golden tests gdzie to mozliwe).
- **Playwright**: testy smoke UI panelu review.
- **Pre-commit**: format/lint (ruff + black).

## 12. Pakiety i uruchamianie
- **Docker Compose**: lokalne uruchamianie (Postgres, Redis, MinIO).
- **uv** lub **poetry**: zarządzanie zależnościami Python.
- **Makefile**: wygodne taski (build, render, run, migrate).

### Uwaga: macOS (Apple Silicon, M2) i odporność na zmiany sprzętowe
Jeśli głównym celem jest stabilność środowiska na macOS ARM64 oraz dostępność bibliotek (Godot/FFmpeg), pełna konteneryzacja może nie pomóc, bo Docker działa w VM z Linuksem i nie zapewnia macOS-owych zaleznosci. Zalecane podejście:
- **Usługi infrastrukturalne w Compose** (Postgres/Redis/MinIO).
- **Godot i FFmpeg natywnie na macOS** z twardo przypiętymi wersjami.
- **Pinning zależności**: `pyproject` + lock (`uv`/`poetry`), opcjonalnie `constraints.txt`.
- **Bootstrap środowiska**: `Brewfile` + `scripts/setup-macos.sh` dla powtarzalnego setupu.

## Rekomendowany minimalny zestaw (start MVP)
1. Python + FastAPI + RQ + Redis
2. Postgres + Alembic
3. Godot 4.x + GDScript + Movie Maker (+ opcjonalnie FFmpeg)
4. React + Vite panel review
5. Lokalny storage dla wideo

## Plan migracji z MVP do wersji docelowej
1. **Etap 0 (MVP)**: Godot 4.x + GDScript, lokalny storage, podstawowa observability.
2. **Etap 1 (Stabilizacja)**:
   - Walidacja skryptu + ograniczenia runtime.
   - Tryb preview vs final render.
3. **Etap 2 (Hardening)**:
   - Kontrakt bledow i petla naprawy LLM.
   - Sandboxing w projekcie Godot (brak IO/sieci, limity zasobow).
4. **Etap 3 (Storage i skala)**:
   - Przenieść artefakty do MinIO/S3.
   - Dodać polityki retencji i lifecycle dla odrzuconych renderów.
5. **Etap 4 (Operacyjność)**:
   - Dodać tracing (OpenTelemetry), jeśli rośnie liczba jobów.
   - Rozważyć Celery, gdy workflow wymaga złożonych retry i zależności.

## Uzasadnienie wyboru
- **Szybkość iteracji**: Python i FastAPI minimalizują koszt zmian i eksperymentów.
- **Najkrotsza droga do animacji**: Godot ma wbudowana fizyke i render, wiec redukuje koszt budowy silnika od zera.
- **Elastycznosc kreatywna**: pelny skrypt GDScript pozwala na szerokie spektrum zachowan i scen.
- **Czytelny pipeline**: job queue + statusy w DB = proste debugowanie.
- **Skalowalność w przyszłości**: łatwa migracja do chmury (S3, K8s) bez przebudowy architektury.

## Uwagi dot. bezpieczeństwa (MVP)
- **Przechowywanie kluczy**: `.env`/vault lokalny + ograniczone uprawnienia plików.
- **Auth**: session-based + Argon2, logowanie zdarzeń i nieudanych prób.
- **Panel**: podstawowy rate limiting i blokada publikacji bez konfiguracji kluczy.
# Generator pomyslow + skryptow (modul)
- **Provider**: OpenAI API / lokalny LLM (opcjonalnie) jako generator pomyslow i pelnych skryptow GDScript.
- **Fallback**: statyczny plik `.ai/ideas.md` dla opisow + odrzut, gdy brak poprawnego skryptu.
- **Embedding**: docelowo embeddingi modelowe (np. OpenAI) zamiast hash‑embeddingu.

# Embedding Service (moduł)
- **Provider**: OpenAI embeddings / lokalny model (opcjonalnie).
- **Cache + retry + rate limit**: ochrona kosztów i stabilność.
- **Fallback**: hash‑embedding w trybie offline.
