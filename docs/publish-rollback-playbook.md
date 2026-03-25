# Publish Rollback Playbook

Data: 2026-03-24  
Cel: szybki i bezpieczny fallback z automatyzacji publish do trybu manualnego.

## 1. Triggery rollback
- `publish-readiness-check` kończy się błędem.
- `publish-oauth-smoke` online zgłasza `failed`.
- Wykryte naruszenie ToS/compliance lub incydent bezpieczeństwa tokenów.

## 2. Kroki rollback
1. Wyłącz automatyczne publikowanie (pozostaw tylko zapis `manual_confirmed`).
2. Wymuś ręczny flow operatora (`QC -> Publish Record (manual)`).
3. Oznacz incydent w logu operacyjnym i dodaj wpis do `TODO.md`.
4. W razie ryzyka token leakage: natychmiastowa rotacja sekretów.
5. Uruchom ponownie gate po naprawie:
   - `make mcp-publish-audit`
   - `make mcp-compliance-check`
   - `make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1 OAUTH_SMOKE_REQUIRE=passed_if_configured`

## 3. Kryterium powrotu do auto-trial
- Compliance checklist: verdict `pass`.
- OAuth smoke online: `passed` dla skonfigurowanych providerów.
- Brak otwartych ryzyk krytycznych w `TODO.md`.
