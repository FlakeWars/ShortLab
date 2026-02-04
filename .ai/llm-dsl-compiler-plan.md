# LLM Idea -> DSL - execution-ready plan (2 modulowy)

## 0. Cel i zasada naczelna
- Rozdzielamy odpowiedzialnosc:
  - **Modul A: DSL Capability Verifier** decyduje czy idea jest wykonalna w aktualnym DSL.
  - **Modul B: Idea->DSL Compiler** kompiluje tylko idee wykonalne.
- Kompilator nie zastanawia sie "czy DSL wystarcza", to jest odpowiedzialnosc Verifiera.

---

## 1. Kontekst i zaleznosci

### 1.1 Zrodla danych (must-have)
- Idee: tabela `idea` (lub aktualny model repo).
- Rejestr brakow DSL: `dsl_gap`.
- Powiazania idea-gap: `idea_gap_link`.
- Spec DSL:
  - `/.ai/dsl-v1.md` (kanoniczny opis semantyki),
  - `/.ai/db-plan.md` (kontrakt danych),
  - szablon bazowy DSL, np. `/.ai/examples/dsl-v1-happy.yaml`.

### 1.2 Wersjonowanie kontekstu
- `dsl_version` (np. `v1`).
- `verification_policy_version` (reguly Verifiera).
- `compiler_prompt_version` (prompt kompilatora).
- `repair_prompt_version` (prompt naprawczy).

---

## 2. Modul A - DSL Capability Verifier

## 2.1 Wejscie (kontrakt runtime)
```json
{
  "idea_id": "uuid",
  "dsl_version": "v1",
  "verification_policy_version": "capability-v1",
  "resources": {
    "idea_source": "db",
    "dsl_spec_path": ".ai/dsl-v1.md",
    "gap_registry_source": "db",
    "examples_path": ".ai/examples"
  },
  "dedupe": {
    "enabled": true,
    "strategy": "gap_key_v1"
  }
}
```

## 2.2 Wyjscie (kontrakt runtime)
```json
{
  "idea_id": "uuid",
  "dsl_version": "v1",
  "feasible": false,
  "new_gap_ids": ["uuid"],
  "existing_gap_ids": ["uuid"],
  "verification_report": {
    "summary": "text",
    "confidence": 0.87,
    "evidence": [
      "requires motion blur",
      "requires volumetric light"
    ]
  }
}
```

## 2.3 Zasady decyzji `feasible`
- `feasible = true`, gdy:
  - wszystkie wymagane cechy idei da sie odwzorowac przez aktualny DSL i renderer MVP.
- `feasible = false`, gdy:
  - co najmniej jedna cecha krytyczna nie ma reprezentacji w DSL lub rendererze.

## 2.4 Wazny przypadek: `NO` bez nowych gapow
- Jesli idea jest niewykonalna, ale wszystkie brakujace cechy sa juz w `dsl_gap`:
  - `feasible = false`,
  - `new_gap_ids = []`,
  - `existing_gap_ids != []`.

## 2.5 Deduplikacja gapow
- Dla kazdego wykrytego braku Verifier wylicza `gap_key`:
  - normalizacja `feature + reason + scope(dsl_version)`,
  - hash SHA-256 -> skracany identyfikator.
- Najpierw szuka po `gap_key`:
  - istnieje -> linkuje idee do gapa,
  - brak -> tworzy nowy rekord `dsl_gap`.

## 2.6 Statusy idei (po Verifierze)
- `unverified` -> `feasible` lub `blocked_by_gaps`.
- Gdy wszystkie linkowane gapy maja `implemented`:
  - idea przechodzi do `ready_for_gate` (automatycznie po re-verification).

---

## 3. Rejestr DSL Gaps

## 3.1 Model danych (minimalny)
- `dsl_gap`:
  - `id` (uuid),
  - `gap_key` (unique),
  - `dsl_version`,
  - `feature`,
  - `reason`,
  - `impact`,
  - `status`: `new|accepted|in_progress|implemented|rejected`,
  - `created_at`, `updated_at`.
- `idea_gap_link`:
  - `idea_id`,
  - `dsl_gap_id`,
  - `detected_at`,
  - unique(`idea_id`, `dsl_gap_id`).

## 3.2 Reguly operacyjne
- Nie kasujemy gapow historycznych (auditability).
- Zmiana statusu `dsl_gap` na `implemented` triggeruje re-verification powiazanych idei.

---

## 4. Modul B - Idea->DSL Compiler

## 4.1 Precondition
- Kompilator przyjmuje tylko idee o statusie:
  - `feasible` lub `ready_for_gate`.
- Jesli status inny -> twardy blad `idea_not_feasible`.

## 4.2 Wejscie (kontrakt runtime)
```json
{
  "idea_id": "uuid",
  "dsl_version": "v1",
  "template_path": ".ai/examples/dsl-v1-happy.yaml",
  "compiler_prompt_version": "idea-to-dsl-v1",
  "repair_prompt_version": "idea-to-dsl-repair-v1",
  "limits": {
    "max_attempts": 3,
    "max_repairs": 2
  }
}
```

## 4.3 Wyjscie (kontrakt runtime)
```json
{
  "idea_id": "uuid",
  "dsl_path": "out/.../dsl.yaml",
  "dsl_hash": "sha256",
  "compiler_meta": {
    "provider": "openai",
    "model": "gpt-5",
    "compiler_prompt_version": "idea-to-dsl-v1",
    "repair_prompt_version": "idea-to-dsl-repair-v1",
    "attempt_count": 2,
    "repair_count": 1
  },
  "validation_report": {
    "syntax_ok": true,
    "semantic_ok": true,
    "quality_warnings": []
  }
}
```

## 4.4 Petla kompilacji
1. `generate` (LLM tworzy YAML).
2. `syntax validate`.
3. `semantic validate`.
4. Jesli fail -> `repair` (LLM dostaje liste konkretnych bledow).
5. Repeat do limitu.
6. Po limicie:
   - preferowane: `failed` (jawny blad),
   - fallback deterministyczny tylko jako tryb awaryjny, jawnie oznaczony.

## 4.5 Walidacja
- Syntax gate:
  - parse YAML,
  - zgodnosc ze schema/model.
- Semantic gate:
  - poprawne referencje (`entity_id`, `applies_to`),
  - sensowne zakresy runtime,
  - brak pustej animacji.
- Quality gate (soft):
  - ostrzezenia, nie blokada (MVP).

---

## 5. Integracja z calym flow produktu

## 5.1 Rytmy procesow
- Idea Generator: dziala swoim rytmem, dodaje idee jako `unverified`.
- Verifier: dziala asynchronicznie i stale obrabia `unverified` + idee wymagajace re-verification.
- Idea Gate: pobiera tylko `ready_for_gate`.
- Compiler: kompiluje wybrana idee z Gate.
- Potem standardowo: render -> QC -> publikacja -> metryki.

## 5.2 API/Endpointy (proponowane)
- `POST /ideas/verify-capability` (single).
- `POST /ideas/verify-capability/batch`.
- `GET /dsl-gaps` + filtry status/version.
- `POST /dsl-gaps/{id}/status`.
- `POST /ideas/{id}/compile-dsl` (guard: idea feasible only).

---

## 6. Prompty i zasoby dla LLM

## 6.1 Verifier prompt context
- Idea (title, summary, what_to_expect, preview).
- DSL spec (`.ai/dsl-v1.md`).
- Lista juz znanych gapow (`dsl_gap`), zeby unikac duplikatow.
- Instrukcja: zwroc tylko ustrukturyzowany JSON zgodny z kontraktem.

## 6.2 Compiler prompt context
- Idea + wynik Verifiera.
- DSL spec + whitelist pol.
- Bazowy template DSL.
- Twarde instrukcje formatu "tylko YAML".

## 6.3 Repair prompt context
- Ostatni niepoprawny YAML.
- Konkretne bledy walidacji.
- Instrukcja "minimal changes".

---

## 7. Telemetria i KPI

## 7.1 Verifier metrics
- verification throughput,
- feasible ratio,
- gap dedupe ratio,
- liczba przypadkow `NO` bez nowych gapow.

## 7.2 Compiler metrics
- compile success rate,
- repair success rate,
- srednia liczba prob,
- fallback/fail rate,
- koszt i latencja.

## 7.3 KPI MVP
- Verifier:
  - >=95% nowych idei zweryfikowanych w SLA (np. 5 min).
- Compiler:
  - >=85% sukcesu kompilacji dla idei feasible,
  - <=10% fail po repair.

---

## 8. Testy akceptacyjne
- Uzywamy `/.ai/examples/idea-to-dsl-testset.md` (5 idei).
- Scenariusze:
  1. Verifier poprawnie oznacza feasibility.
  2. Dla idei niewykonalnej tworzy/laczy gapy bez duplikatow.
  3. Po `dsl_gap.status=implemented` idea przechodzi do `ready_for_gate`.
  4. Compiler dziala tylko dla idei feasible.
  5. Wygenerowany DSL przechodzi walidacje i render.

---

## 9. Ryzyka i kontrolki
- Ryzyko halucynacji:
  - kontrakty I/O + schema gate + repair.
- Ryzyko dryfu wersji DSL:
  - jawny `dsl_version` wszedzie.
- Ryzyko chaosu w gapach:
  - `gap_key` + dedupe + workflow statusow.

---

## 10. Kolejnosc wdrozenia
1. DB: `dsl_gap`, `idea_gap_link`, statusy idei.
2. Modul A (Verifier) + dedupe + endpointy.
3. Integracja Idea Gate -> tylko `ready_for_gate`.
4. Modul B (Compiler) + validate/repair loop.
5. E2E + dashboard metryk Verifier/Compiler.
