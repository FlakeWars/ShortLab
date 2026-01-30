# ShortLab

ShortLab to lokalny, deterministyczny pipeline do codziennego generowania i publikacji krótkich animacji 2D (Shorts), z panelem review, półautomatyczną publikacją i metrykami dla YouTube/TikTok.

## Zakres MVP
- Generacja DSL -> render -> review/QC -> publikacja -> metryki.
- Deterministyczny render 2D (Skia-Python/Cairo) + FFmpeg.
- Lokalna infrastruktura: Postgres, Redis, MinIO (Docker Compose).
- Panel review: React + Vite.

## Szybki start (macOS M2 Pro)
1. Zainstaluj narzędzia bazowe:
   - `make setup-macos`
2. Zweryfikuj środowisko:
   - `make verify`
3. Utwórz venv i zależności:
   - `make venv`
   - `make deps-py-uv` lub `make deps-py-poetry`
4. Uruchom infrastrukturę:
   - `make infra-up`
5. Uruchom API/worker/UI (gdy kod będzie gotowy):
   - `make api`
   - `make worker`
   - `make ui`

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
