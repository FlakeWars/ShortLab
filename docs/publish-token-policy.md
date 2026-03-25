# Publish Token Policy (Sandbox/Prod)

Data: 2026-03-24  
Zakres: YouTube i TikTok OAuth credentials dla publish/metrics.

## 1. Zasady przechowywania
- Sekrety nie trafiają do repozytorium (`.env`, `.env.local`, manager sekretów).
- Zabronione jest logowanie pełnych tokenów i client secretów.
- Raporty smoke/audit używają maskowania tokenów.

## 2. Minimalny kontrakt sekretów
- YouTube:
  - `YOUTUBE_CLIENT_ID`
  - `YOUTUBE_CLIENT_SECRET`
  - `YOUTUBE_REFRESH_TOKEN`
- TikTok:
  - `TIKTOK_CLIENT_KEY`
  - `TIKTOK_CLIENT_SECRET`
  - `TIKTOK_REFRESH_TOKEN`

## 3. Rotacja
- Rotacja tokenów po incydencie bezpieczeństwa lub po zmianie ownera konta.
- Rotacja planowa cykliczna zgodnie z polityką organizacji.
- Po rotacji: obowiązkowo `make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1 OAUTH_SMOKE_REQUIRE=passed_if_configured`.

## 4. Dostępy
- Least privilege: scope tylko dla operacji wymaganych przez aktualny etap flow.
- Dostęp do sekretów tylko dla operatorów i automatyzacji odpowiedzialnej za publikację.

## 5. Kontrola przed publikacją
- `make mcp-publish-audit`
- `make mcp-compliance-check`
- `make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1 OAUTH_SMOKE_REQUIRE=passed_if_configured`
- opcjonalnie całość: `make publish-readiness-check` (plus online smoke przez env override)
