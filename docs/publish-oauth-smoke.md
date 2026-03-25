# Publish OAuth Smoke

Data: 2026-03-24  
Cel: szybka walidacja odświeżania tokenów OAuth dla YouTube i TikTok w środowisku sandbox.

## 1. Uruchomienie

Tryb bezpieczny (offline, bez requestów do providerów):
```bash
make publish-oauth-smoke
```

Tryb online (realne requesty refresh token):
```bash
make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1
```

## 2. Polityka fail-fast

Domyślnie skrypt nie failuje pipeline (`OAUTH_SMOKE_REQUIRE=none`).

Opcje:
- `OAUTH_SMOKE_REQUIRE=passed_if_configured`:
  - fail tylko gdy provider ma skonfigurowane env, ale refresh nie przejdzie.
- `OAUTH_SMOKE_REQUIRE=passed_all`:
  - fail jeśli oba providery nie przejdą statusem `passed`.

Przykład:
```bash
make publish-oauth-smoke OAUTH_SMOKE_ONLINE=1 OAUTH_SMOKE_REQUIRE=passed_if_configured
```

## 3. Wymagane env (online refresh)

YouTube:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

TikTok:
- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_REFRESH_TOKEN`

## 4. Artefakty

- `out/reports/publish-oauth-smoke-<timestamp>.json`
- `out/reports/publish-oauth-smoke-<timestamp>.md`
- `out/reports/publish-oauth-smoke-latest.json`
- `out/reports/publish-oauth-smoke-latest.md`

## 5. Endpointy źródłowe

- Google OAuth token endpoint: `https://oauth2.googleapis.com/token`
- TikTok OAuth token endpoint: `https://open.tiktokapis.com/v2/oauth/token/`

## 6. Zasady bezpieczeństwa

- Raport maskuje tokeny (nie zapisuje pełnych wartości).
- Test uruchamiaj na kontach sandbox/testowych.
- Po testach produkcyjnych rekomendowana rotacja tokenów zgodnie z polityką platform.
