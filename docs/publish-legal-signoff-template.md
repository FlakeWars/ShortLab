# Publish Automation Legal Sign-off (Template)

Data: 2026-03-24  
Zakres: trial automatyzacji publish/analytics (YouTube, TikTok)

## 1) Decyzja
- YouTube ToS scope: `approved | rejected`
- TikTok ToS scope: `approved | rejected`

## 2) Zakres automatyzacji objęty zgodą
- Publish: `manual_confirmed` + opcjonalny auto-upload API
- Metrics: odczyt metryk API zgodnie z matrycą scope
- Brak automatyzacji działań poza zakresem (komentarze/DM/moderacja)

## 3) Potwierdzenie zgodności
- Zgodność z `docs/publish-oauth-scope-matrix.md`
- Zgodność z `docs/publish-token-policy.md`
- Zgodność z `docs/publish-rollback-playbook.md`

## 4) Ograniczenia i warunki
- Konta sandbox przed produkcją: `tak/nie`
- Wymagany online smoke OAuth przed trialem: `tak`
- Warunki stopu (incident trigger):
  - naruszenie ToS,
  - błędy publikacji powyżej ustalonego progu,
  - incydent bezpieczeństwa tokenów.

## 5) Akceptacje
- Owner biznesowy:
  - Imię i nazwisko:
  - Data:
  - Podpis/akceptacja:
- Owner techniczny:
  - Imię i nazwisko:
  - Data:
  - Podpis/akceptacja:
- Legal/Compliance:
  - Imię i nazwisko:
  - Data:
  - Podpis/akceptacja:

## 6) Kroki po akceptacji
1. Ustawić `decision=approved` dla serwerów w `docs/mcp-compliance-checklist.json`.
2. Uruchomić `make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1 OAUTH_SMOKE_REQUIRE=passed_if_configured`.
3. Uruchomić `make mcp-compliance-check` (strict, oczekiwany `pass`).
4. Uruchomić `make publish-readiness-check` i potwierdzić `overall_pass=true`.
