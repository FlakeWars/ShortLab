# AGENTS

Ten plik opisuje lokalne zasady współpracy z agentem i minimalny „contract” pracy w repozytorium.

## Zasady
- Preferuj `Makefile` jako pojedynczy interfejs uruchomieniowy.
- Skrypty trzymamy w `scripts/` i wywołujemy je z Makefile.
- Infrastruktura uruchamiana przez Docker Compose (Postgres/Redis/MinIO).
- Renderer i FFmpeg uruchamiane natywnie na macOS ARM64.
- Zależności Python: `pyproject.toml` + lock (uv/poetry).
- Zmiany wersji: przez `Brewfile`, `versions.env` i lockfile.
- TODO projektu prowadzimy w `TODO.md` w root i przestrzegamy zasad z tego pliku.
- Nie zmieniamy wersji narzędzi ani zależności bez wyraźnej zgody użytkownika; zawsze trzymamy się `versions.env`.
- Po realizacji każdego podpunktu z `TODO.md` raportujemy krótko: co zrobione, co nieudane/blokady i jaki jest stan.
- Po realizacji każdego podpunktu robimy krytyczną analizę efektu; może to skutkować zmianami w `TODO.md`, dokumentacji (`.ai/prd.md`, `.ai/tech-stack.md`, `README.md` lub innych plikach), a także dopisaniem nowych zasad/zakazów w `AGENTS.md` i zmianą kolejnego kroku.
- Dokumentacja musi być spójna z `versions.env`; przy rozbieżnościach aktualizujemy dokumentację, nie wersje.

## Commitowanie i merge
- Jeden temat na raz: dla każdej pracy tworzymy osobną gałąź.
- Każdy commit poprzedzamy uruchomieniem formatterów i linterów.
- Commit wykonujemy tylko jeśli narzędzia jakości przechodzą bez błędów.
- Wiadomości commitów muszą spełniać Conventional Commits (patrz `/.ai/conventional-commits.md`).
- Merge do `main` tylko po zakończeniu zadania i testach, oraz wyłącznie za zgodą użytkownika.
- Operacje: tworzenie gałęzi, commit i merge wykonujemy tylko na wyraźną prośbę użytkownika.
- Wszystkie działania git kończymy push do zdalnego repozytorium.

## Pliki referencyjne
- `/.ai/prd.md`
- `/.ai/tech-stack.md`
- `/.ai/bootstrap.md`
- `/versions.env`
- `/.ai/conventional-commits.md`
