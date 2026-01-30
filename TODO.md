# TODO

## Now (W toku)
- [ ] Dev environment bootstrap (branch: chore/dev-setup)
  - [ ] Zweryfikować i uzupełnić środowisko dev na macOS (Brewfile + versions.env)
  - [ ] Przygotować skrypt bootstrapu macOS (scripts/setup-macos.sh) i wpisać do Makefile
  - [ ] Spisać minimalne kroki uruchomienia lokalnego (README: 5-min quickstart)
- [ ] DSL v1 + walidacja (branch: feat/dsl-v1)
  - [ ] Opisać DSL v1: struktura pliku, pola wymagane, opcjonalne, wersjonowanie
  - [ ] Zdefiniować minimalny kontrakt FSM (stany, przejścia, parametry, wejścia/wyjścia)
  - [ ] Przygotować 2 przykładowe pliki DSL v1 (happy path + edge case)
  - [ ] Wybrać format wejścia (JSON albo YAML) i uzasadnić w krótkiej notce
  - [ ] Zaimplementować schemat DSL (pydantic/jsonschema) + walidator wejścia
  - [ ] Dodać testy walidacji DSL (min. valid/invalid cases)
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
