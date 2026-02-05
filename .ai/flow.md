# Flow E2E (IdeaCandidate -> Idea -> DSL -> Render -> Publish)

Poniżej jest aktualny, krok po kroku, opis przeplywu systemu po zmianie na weryfikacje DSL po stronie **IdeaCandidate**.

## 1) Generowanie pomyslow (Idea Generator)
- Wejscie: konfiguracja generatora + prompt.
- Wyjscie: rekordy `idea_candidate` (status=`new`, capability_status=`unverified`) powiazane z `idea_batch`.
- Dodatkowo: ustawiany `similarity_status` (ok/too_similar/unknown).
- Fallback: statyczne pomysly z pliku, gdy brak LLM.

## 2) Weryfikacja mozliwosci DSL (Capability Verifier) - na kandydacie
- Wejscie: `idea_candidate` z capability_status=`unverified`.
- Akcja: analiza tekstu kandydata vs aktualny DSL (reguly + sygnaly).
- Jesli brakuje funkcji: tworzy/odnajduje `dsl_gap`, linkuje przez `idea_candidate_gap_link`.
- Wyjscie:
  - `idea_candidate.capability_status = feasible` (gdy brak blokujacych gapow)
  - albo `idea_candidate.capability_status = blocked_by_gaps`
- (Opcjonalnie) Jesli kandydat ma juz powiazana `idea`, aktualizuje jej status na `ready_for_gate` / `blocked_by_gaps`.

## 3) Idea Gate (wybor operatora)
- Wejscie: kandydaci z `status in (new,later)` oraz `capability_status=feasible`.
- UI losuje N kandydatow (/idea-repo/sample) i wymusza klasyfikacje:
  - `picked` (dokladnie jeden)
  - `later` (zostaje w repozytorium)
  - `rejected` (usuniecie kandydata)
- Wyjscie:
  - kandydat `picked` -> `idea_candidate.status = picked`
  - tworzy sie `idea` powiazana z kandydatem, `idea.status = ready_for_gate`
  - audit event zapisywany w DB

## 4) Uruchomienie pipeline (enqueue)
- Wejscie: `idea_id` z kroku 3.
- Akcja: `/ops/enqueue` uruchamia pipeline z wybrana idea.
- Wyjscie: joby w kolejce (generate_dsl -> render).

## 5) Kompilacja Idea -> DSL
- Wejscie: `idea` w stanie `ready_for_gate` (albo `feasible`).
- Akcja: LLM DSL Compiler (generate -> validate -> repair -> retry -> fallback).
- Wyjscie:
  - zapis `dsl.yaml` w `out_root`
  - `idea.status = compiled`
  - raport walidacji + metadata kompilacji

## 6) Render
- Wejscie: DSL + parametry renderu.
- Akcja: renderer (Cairo/Skia) + FFmpeg.
- Wyjscie:
  - rekordy `animation`, `render`
  - `artifacts` (wideo + metadata)
  - pipeline stage `render`

## 7) QC (manual)
- Wejscie: render + artefakty.
- Akcja: operator podejmuje decyzje QC (accept/reject/regenerate).
- Wyjscie: zapis `qc_decision`, aktualizacja statusu animacji.
- Status: panel QC w UI jest w backlogu (planowane).

## 8) Publikacja
- Wejscie: zaakceptowana animacja.
- Akcja: publish (YouTube/TikTok) przez ujednolicony interfejs platform.
- Wyjscie: `publish_record` + status publikacji.
- Status: panel publikacji w UI jest w backlogu (planowane).

## 9) Metryki i feedback
- Wejscie: opublikowana animacja + platforma.
- Akcja: pull metryk dziennych + analiza.
- Wyjscie: metryki w DB + insighty dla generatora idei.
- Status: modul feedback/analytics planowany.

---

## Sprzezenia zwrotne (petle)
- **Dsl Gap -> Reverify**: zmiana `dsl_gap.status` na `implemented` uruchamia re-verification
  kandydatow (i idei), odblokowujac wczesniej zablokowane propozycje.
- **Kompilator -> Repair**: jesli DSL nie przejdzie walidacji, uruchamia sie petla repair/retry.
- **Render -> Rerun**: nieudany render moze zostac uruchomiony ponownie (rerun).

## Najwazniejsze stany
- `idea_candidate.status`: `new | later | picked`
- `idea_candidate.capability_status`: `unverified | feasible | blocked_by_gaps`
- `idea.status`: `ready_for_gate | compiled` (pozostale statusy sa legacy i moga byc widoczne)
- `dsl_gap.status`: `new | accepted | in_progress | implemented | rejected`

## Wazne uwagi
- **Idea Gate operuje na kandydacie**, nie na idei. Idea powstaje dopiero po decyzji `picked`.
- Weryfikacja DSL (capability) jest wykonywana **przed** Idea Gate i filtruje propozycje.
- Jesli nie ma zadnych feasible kandydatow, Idea Gate zwraca pusta liste.
