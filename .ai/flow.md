# Flow E2E (IdeaCandidate -> GDScript -> Preview -> Render -> Publish)

Poniżej nowy, uproszczony przeplyw oparty o pelny skrypt GDScript generowany przez LLM i render w Godot 4.x.

## 1) Generowanie pomyslu + skryptu (LLM)
- Wejscie: prompt z ograniczona pula node/shape, czasem max i limitem obiektow.
- Wyjscie: rekord `idea_candidate` z opisem + pelnym skryptem GDScript.
- Dodatkowo: obliczany embedding i similarity do historii.

## 2) Walidacja skryptu (smoke test) + petla naprawy
- Wejscie: `idea_candidate` z `status=new` i skryptem.
- Akcja: parse + load + krotki tick fizyki (np. 1-2 sekundy).
- Jesli bledy:
  - raport (sciezka -> expected -> got),
  - LLM repair (limit prob).
- Wyjscie:
  - `script_status=valid` albo `script_status=invalid` po limicie.

## 3) Idea Gate (wybor operatora)
- Wejscie: kandydaci ze `script_status=valid`.
- UI losuje N kandydatow i wymusza klasyfikacje:
  - `picked` (dokladnie jeden)
  - `later`
  - `rejected`
- Wyjscie: `picked` przechodzi do preview/render.

## 4) Preview render (opcjonalnie, zalecane)
- Wejscie: skrypt z `picked`.
- Akcja: Godot Movie Maker w trybie preview (niska rozdzielczosc / krotki klip).
- Wyjscie: podglad wideo do decyzji operatora.

## 5) Render finalny
- Wejscie: `picked` + (opcjonalnie) zaakceptowany preview.
- Akcja: Godot Movie Maker renderuje finalne wideo.
- Wyjscie: artefakty wideo + metadane (hash skryptu, wersja Godot, parametry).

## 6) QC (manual)
- Wejscie: render + artefakty.
- Akcja: operator podejmuje decyzje QC (accept/reject/regenerate).
- Wyjscie: zapis `qc_decision`, aktualizacja statusu animacji.
- Jesli `regenerate`: notatka trafia do LLM jako wejscie do naprawy skryptu.

## 7) Publikacja
- Wejscie: zaakceptowana animacja.
- Akcja: publish (YouTube/TikTok) przez ujednolicony interfejs platform.
- Wyjscie: `publish_record` + status publikacji.

## 8) Metryki i feedback
- Wejscie: opublikowana animacja + platforma.
- Akcja: pull metryk dziennych + analiza.
- Wyjscie: metryki w DB + insighty dla generatora idei.

---

## Sprzezenia zwrotne (petle)
- **Walidacja -> Repair**: bledy skryptu wracaja do LLM w tej samej sesji.
- **QC -> Repair**: notatka operatora powoduje naprawe skryptu i nowy preview/render.

## Najwazniejsze stany (proponowane)
- `idea_candidate.status`: `new | later | picked | rejected`
- `idea_candidate.script_status`: `unverified | valid | invalid`
- `animation.status`: `rendered | qc_accepted | qc_rejected | published`

## Wazne uwagi
- Skrypt GDScript jest glownym kontraktem; brak osobnego DSL w MVP.
- Legacy DSL pipeline pozostaje w repo, ale nie jest kierunkiem rozwojowym.
