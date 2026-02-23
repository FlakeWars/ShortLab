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
- Każde zidentyfikowane ryzyko, brak lub możliwa korekta **musi** zostać dodane jako podpunkt w `TODO.md`.
- Dokumentacja musi być spójna z `versions.env`; przy rozbieżnościach aktualizujemy dokumentację, nie wersje.
- Po zakończeniu zadania (branch-level) wykonujemy merge do `main`, przełączamy się na `main` i robimy `git pull`. Dopiero potem uznajemy zadanie za zamknięte.
- Po merge do `main` wykonujemy krótką analizę wpływu na plan: czy pojawiły się nowe priorytety lub czy kolejność zadań w `TODO.md` wymaga korekty. Zmiany zapisujemy w `TODO.md`/dokumentacji zanim startujemy kolejne zadanie.
- Po **każdym** merge do `main` wykonujemy obowiązkowy przegląd i synchronizację dokumentacji (`README.md`, `.ai/prd.md`, `.ai/tech-stack.md` oraz innych dotkniętych plików), tak aby odzwierciedlała faktyczny stan implementacji; wynik przeglądu zapisujemy w `TODO.md`.
- Po wykryciu nowych modułów/zależności dopisujemy je do `TODO.md` od razu na bieżącym branchu, a po powrocie na `main` wykonujemy „sync TODO”, aby lista modułów była kompletna.
- Unikamy ręcznych komend. Jeśli coś wymaga ręcznego uruchomienia, dodajemy/aktualizujemy target w `Makefile` lub skrypt wywoływany przez `Makefile`.
- Unikamy nawarstwiających się warningów; jeśli się pojawiają, dodajemy podpunkt na ich usunięcie.
- Przed każdym commitem sprawdzamy `git status -sb` i upewniamy się, że wszystkie zmiany związane z zadaniem są zarejestrowane (bez pomijania plików).
- TODO utrzymujemy w porządku na bieżąco: tylko aktywne zadanie w sekcji Now, reszta w Next/Done; po każdej zmianie natychmiast korygujemy sekcje i podzadania.
- Sekcja `Now` w `TODO.md` jest powiązana z aktywną gałęzią roboczą:
  - na branchu roboczym: tylko aktualnie realizowany temat tej gałęzi,
  - na `main`: sekcja `Now` musi być pusta (brak aktywnej implementacji na `main`).

## Commitowanie i merge
- Jeden temat na raz: dla każdej pracy tworzymy osobną gałąź.
- Utworzenie/przełączenie na gałąź roboczą przed zmianami kodu jest domyślne (chyba że użytkownik wyraźnie zleci pracę na `main`).
- Każdy commit poprzedzamy uruchomieniem formatterów i linterów.
- Commit wykonujemy tylko jeśli narzędzia jakości przechodzą bez błędów.
- Wiadomości commitów muszą spełniać Conventional Commits (patrz `/.ai/conventional-commits.md`).
- Merge do `main` tylko po zakończeniu zadania i testach, oraz wyłącznie za zgodą użytkownika.
- Operacje: commit, merge i push wykonujemy tylko na wyraźną prośbę użytkownika.
- Jeśli praca została wykonana omyłkowo na `main`, przed kolejnym zadaniem należy odnotować to w `TODO.md` (process debt) i wrócić do workflow branchowego.
- Wszystkie działania git kończymy push do zdalnego repozytorium.

### Checklista branch workflow (obowiązkowa przy pracy z kodem)
1. Przed pierwszą zmianą w kodzie sprawdź `git status -sb` i bieżącą gałąź.
2. Jeśli jesteś na `main`, utwórz/przełącz na gałąź roboczą (chyba że użytkownik wyraźnie kazał pracować na `main`).
3. Wykonaj zmiany i aktualizuj `TODO.md` na bieżąco (postęp + ryzyka + krytyczna analiza).
4. Przed commitem uruchom formattery/lintery/testy właściwe dla zakresu zmian.
5. Przed commitem ponownie sprawdź `git status -sb` i upewnij się, że komplet zmian zadania jest ujęty.
6. Commit/merge/push wykonuj tylko po wyraźnej prośbie użytkownika.
7. Przed merge upewnij się, że zadanie zostało przeniesione z `Now` do `Done`/`Next` i `Now` jest puste.
8. Po merge do `main` wykonaj `git pull` i obowiązkowy sync dokumentacji + wpis do `TODO.md`; potwierdź, że `Now` na `main` jest puste.

## Pliki referencyjne
- `/.ai/prd.md`
- `/.ai/tech-stack.md`
- `/.ai/bootstrap.md`
- `/versions.env`
- `/.ai/conventional-commits.md`
