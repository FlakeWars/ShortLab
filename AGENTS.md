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
- Po każdej krytycznej analizie zapisujemy wynik w `TODO.md` (np. nowe podpunkty/zakres v1.1), żeby nie zgubić ważnych uwag.
- Dokumentacja musi być spójna z `versions.env`; przy rozbieżnościach aktualizujemy dokumentację, nie wersje.
- Po zakończeniu zadania (branch-level) wykonujemy merge do `main`, przełączamy się na `main` i robimy `git pull`. Dopiero potem uznajemy zadanie za zamknięte.
- Po merge do `main` wykonujemy krótką analizę wpływu na plan: czy pojawiły się nowe priorytety lub czy kolejność zadań w `TODO.md` wymaga korekty. Zmiany zapisujemy w `TODO.md`/dokumentacji zanim startujemy kolejne zadanie.
- Unikamy ręcznych komend. Jeśli coś wymaga ręcznego uruchomienia, dodajemy/aktualizujemy target w `Makefile` lub skrypt wywoływany przez `Makefile`.
- Unikamy nawarstwiających się warningów; jeśli się pojawiają, dodajemy podpunkt na ich usunięcie.
- Przed każdym commitem sprawdzamy `git status -sb` i upewniamy się, że wszystkie zmiany związane z zadaniem są zarejestrowane (bez pomijania plików).

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
