# MCP Publish Audit

Data: 2026-03-24  
Cel: formalna ocena gotowości serwerów MCP do trialu publish/analytics, bez ryzyka dla krytycznego flow publikacji.

## 1. Zakres
- Audyt dotyczy wyłącznie warstwy MCP (assist/trial), nie zastępuje oficjalnych API YouTube/TikTok.
- Krytyczny publish flow pozostaje na natywnych integracjach API + fallback `manual_confirmed`.

## 2. Uruchomienie
```bash
make mcp-publish-audit
```

Opcjonalnie:
```bash
make mcp-publish-audit \
  MCP_AUDIT_SERVERS='io.github.wmarceau/youtube-creator,io.github.wmarceau/tiktok-creator' \
  MCP_AUDIT_OUT_DIR='out/reports' \
  MCP_AUDIT_FAIL_ON_RISK_LEVEL='high'
```

## 3. Co sprawdza audyt
- Official MCP Registry:
  - obecność `latest` wersji,
  - status oficjalny (`active`),
  - metadane pakietu i transport.
- Repozytorium źródłowe (GitHub API):
  - czy repo nie jest zarchiwizowane,
  - licencja SPDX,
  - świeżość utrzymania (ostatni push <= 180 dni),
  - podstawowe sygnały aktywności (stars/forks/issues).
- Kontrakt env dla serwerów publish:
  - youtube creator: `YOUTUBE_CREDENTIALS_PATH`, `YOUTUBE_TOKEN_PATH`,
  - tiktok creator: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`.

## 4. Artefakty
- JSON: `out/reports/mcp-publish-audit-<timestamp>.json`
- Markdown: `out/reports/mcp-publish-audit-<timestamp>.md`
- latest symlink-like copies (nadpisywane):
  - `out/reports/mcp-publish-audit-latest.json`
  - `out/reports/mcp-publish-audit-latest.md`

## 5. Decyzja gate
- `eligible_for_trial`: można uruchomić sandboxowy trial.
- `trial_only_with_mitigations`: tylko trial z dodatkowymi zabezpieczeniami.
- `reject_for_trial`: brak zgody na trial do czasu usunięcia ryzyk krytycznych.
- CI gate (opcjonalny): `MCP_AUDIT_FAIL_ON_RISK_LEVEL=high|medium` wymusza exit code `2` przy przekroczeniu progu ryzyka.

## 6. Zasada bezpieczeństwa
- Nawet przy `eligible_for_trial`, MCP nie przejmuje krytycznego publish flow.
- Wymagane pozostaje:
  - fallback manualny,
  - obserwowalność i audit eventy,
  - zgodność z ToS platform i polityką tokenów.

## 7. Pipeline gate (zbiorczy)

Możesz uruchomić pełny zestaw gate:
```bash
make publish-readiness-check
```

Domyślnie:
- `mcp-publish-audit` failuje przy `risk_level >= high`,
- `mcp-compliance-check` działa w `strict`,
- `publish-oauth-smoke` działa jako `passed_if_configured`.

Dodatkowo:
```bash
make publish-readiness-summary
```
agreguje latest raporty do jednego statusu `overall_pass`.
