# MCP Compliance Check

Data: 2026-03-24  
Cel: formalny, powtarzalny gate compliance przed trialem MCP dla publish/analytics.

## 1. Pierwsze uruchomienie

```bash
make mcp-compliance-check MCP_COMPLIANCE_REQUIRE=none
```

Jeśli plik checklisty nie istnieje, zostanie utworzony z template:
- template: `docs/mcp-compliance-checklist.template.json`
- checklist: `docs/mcp-compliance-checklist.json`

## 2. Wypełnienie checklisty

Dla każdego serwera MCP:
- ustaw `decision`: `approved|rejected|pending`
- dla każdego itemu ustaw `status`: `passed|failed|waived|pending`
- dla `passed`/`waived` uzupełnij `evidence`.
- dla pozycji `least_privilege_scopes` użyj matrycy: `docs/publish-oauth-scope-matrix.md`.
- dla pozycji `tos_allowed_usage` użyj procesu akceptacji z `docs/publish-legal-signoff-template.md`.

## 3. Walidacja (strict)

```bash
make mcp-compliance-check
```

Domyślnie `MCP_COMPLIANCE_REQUIRE=strict`:
- zwraca `exit code 2`, jeśli verdict != `pass`.

## 4. Artefakty

- `out/reports/mcp-compliance-check-<timestamp>.json`
- `out/reports/mcp-compliance-check-<timestamp>.md`
- `out/reports/mcp-compliance-check-latest.json`
- `out/reports/mcp-compliance-check-latest.md`

## 5. Zasada bramki

Trial MCP można dopuścić dopiero, gdy:
- verdict compliance = `pass`,
- wynik `mcp-publish-audit` nie przekracza uzgodnionego progu ryzyka,
- smoke OAuth sandbox (`publish-oauth-smoke`) jest wykonany dla wymaganych providerów.
