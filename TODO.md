# TODO

## Now (W toku)
- [ ] DSL v1 + walidacja (branch: feat/dsl-v1)
  - [x] Opisać DSL v1: struktura pliku, pola wymagane, opcjonalne, wersjonowanie (2026-01-31)
  - [x] Zdefiniować minimalny kontrakt FSM (stany, przejścia, parametry, wejścia/wyjścia) (2026-01-31)
  - [x] Przygotować 2 przykładowe pliki DSL v1 (happy path + edge case) (2026-01-31)
  - [x] Wybrać format wejścia (JSON albo YAML) i uzasadnić w krótkiej notce (2026-01-31)
  - [x] Zaimplementować schemat DSL (pydantic/jsonschema) + walidator wejścia (2026-01-31)
  - [x] Dodać testy walidacji DSL (min. valid/invalid cases) (2026-01-31)
  - [x] Dodać zależności Python (pyproject + lock) dla DSL/testów (pydantic, pyyaml, pytest) (2026-02-01)
  - [ ] Usunąć warningi Pydantic v2 (Config -> ConfigDict)
- [ ] Minimalny renderer MVP (branch: feat/renderer-mvp)
  - [ ] Renderer Python + Skia/Cairo z deterministycznym seedingiem
  - [ ] Metadane renderu: seed, dsl_version, design_system_version, parametry symulacji

## Next (Kolejne)
- [ ] CLI do renderu (branch: feat/render-cli)
  - [ ] Wejście: DSL + seed, wyjście: wideo + metadane
  - [ ] Walidacja wejścia i czytelne błędy
- [ ] Deterministyczność renderu (branch: test/renderer-golden)
  - [ ] Golden tests (min. 2 przypadki)
  - [ ] Tolerancje porównań i dokumentacja
- [ ] Baza danych + migracje (branch: feat/db-schema)
  - [ ] Szkielet DB (Postgres + Alembic)
  - [ ] Podstawowy model danych: animacja, render, QC, audit
  - [ ] Migracje startowe
- [ ] Minimalny worker pipeline (branch: feat/pipeline-mvp)
  - [ ] RQ + Redis: generacja -> render
  - [ ] Logowanie statusów jobów

## Done (Zrobione)
- [x] Utworzenie TODO.md (branch: chore/todo) (2026-01-30)
  - [x] Zdefiniować strukturę zadań i zasady utrzymania TODO (2026-01-30)
- [x] Dev environment bootstrap (branch: chore/dev-setup) (2026-01-31)
  - [x] Zweryfikować i uzupełnić środowisko dev na macOS (Brewfile + versions.env)
  - [x] Przygotować skrypt bootstrapu macOS (scripts/setup-macos.sh) i wpisać do Makefile (2026-01-30)
  - [x] Wymusić użycie /opt/homebrew w bootstrapie i zweryfikować ścieżkę brew (2026-01-30)
  - [x] Instalować tylko brakujące brew/cask (pomijać istniejący Docker.app) (2026-01-30)
  - [x] Trwale pominąć instalację Docker cask w bootstrapie (2026-01-30)
  - [x] Przenieść wersje Python/Node do mise i dodać .mise.toml (2026-01-31)
  - [x] Zaufać konfiguracji mise (mise trust) (2026-01-31)
  - [x] Naprawić uprawnienia Homebrew i cache (np. /opt/homebrew/Cellar, /opt/homebrew/var/homebrew/locks, ~/Library/Caches/Homebrew) (2026-01-31)
  - [x] Sprawdzić ACL/flags blokujące zapis (np. /opt/homebrew/var/homebrew/locks, ~/Library/Caches/Homebrew) (2026-01-31)
  - [x] Ustawić Node 24 jako aktywny przez mise (2026-01-31)
  - [x] Ustalić, że `make verify` traktuje skia-python i usługi z compose jako opcjonalne (2026-01-31)
  - [x] Usunąć tap `homebrew/bundle` z Brewfile (tap zdeprecjonowany) (2026-01-30)
  - [x] Uruchomić bootstrap lokalnie i potwierdzić działanie (make setup-macos, make verify) (2026-01-31)
  - [x] Spisać minimalne kroki uruchomienia lokalnego (README: 5-min quickstart) (2026-01-31)

## Zasady
- Jeden właściciel taska i jeden cel; task ma kończyć się działającym artefaktem lub testem
- Przenoś zadania między sekcjami tylko przy zmianie statusu (Now -> Done, Next -> Now)
- Dopisuj datę przy ukończonych zadaniach w sekcji Done, np. "(2026-01-30)"
- Zadania główne odpowiadają branchom (jedno zadanie = jeden branch), podzadania realizujemy w ramach tego brancha
- Preferowane prefiksy branchy: `feat/`, `chore/`, `test/`, `docs/`, `fix/`
- Zadanie główne powinno być zamykalne w 1–3 dni robocze; jeśli rośnie, podziel je na dwa branche
- TODO utrzymujemy jako 2 poziomy: tylko zadania główne + podzadania (bez kolejnych poziomów)
- Liczba podzadań jest elastyczna (1–7); przy 1 podzadaniu upewnij się, że branch nadal ma sens
- Przykład małego brancha: dokument/konwencja w jednym pliku (np. TODO, README, RFC-lite)

## Notatki / decyzje
- Docker Desktop instalujemy manualnie (bootstrap pomija cask docker).
- Python/Node instalujemy i pinujemy przez mise (`.mise.toml`).
- `make verify` traktuje skia-python i usługi z compose jako opcjonalne do czasu uruchomienia renderera i infra.
