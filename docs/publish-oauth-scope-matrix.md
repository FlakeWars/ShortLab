# Publish OAuth Scope Matrix (Least Privilege)

Data: 2026-03-24  
Zakres: ShortLab publish/metrics flow (YouTube + TikTok)

## Założenie
ShortLab działa w trybie operator-first i minimalizuje scope'y OAuth do operacji faktycznie używanych w flow:
- publikacja filmu,
- odczyt metryk (tam gdzie używane API),
- identyfikacja konta twórcy potrzebna do UX/publikacji.

## Matryca scope -> operacja

| Platforma | Obszar | Operacja | Minimalny scope | Uwagi |
| --- | --- | --- | --- | --- |
| YouTube | Publish | Upload wideo (`videos.insert`) | `https://www.googleapis.com/auth/youtube.upload` | Scope dedykowany uploadowi; preferowany zamiast szerszego `youtube`. |
| YouTube | Analytics | Odczyt raportów (`reports.query`) | `https://www.googleapis.com/auth/yt-analytics.readonly` | Dla metryk watch-time/engagement bez danych monetarnych. |
| YouTube | Analytics (opcjonalnie) | Raporty przychodowe | `https://www.googleapis.com/auth/yt-analytics-monetary.readonly` | Wymagane tylko jeśli uruchomimy raporty revenue. |
| TikTok | Publish | Direct post przez Content Posting API | `video.publish` | Wymagane zatwierdzenie scope przez TikTok + zgoda użytkownika. |
| TikTok | Account UX (opcjonalnie) | Podstawowe dane profilu twórcy | `user.info.basic` | Używać tylko gdy faktycznie potrzebne do UX/operatora. |

## Scope'y odrzucone (celowo nieużywane)
- YouTube `https://www.googleapis.com/auth/youtube` (zbyt szeroki dla naszego zakresu publish+basic analytics).
- YouTube `https://www.googleapis.com/auth/youtubepartner` (niepotrzebny dla standardowego flow kanału operatora).
- TikTok scope'y niezwiązane z publikacją (np. listowanie treści), o ile nie są wymagane przez konkretny etap produktu.

## Decyzja implementacyjna
- Konfiguracja env i OAuth consent musi prosić tylko o scope'y z tabeli "Minimalny scope".
- Każde rozszerzenie scope'ów wymaga aktualizacji tego pliku, checklisty compliance i ponownego `make mcp-compliance-check`.

## Źródła (oficjalne)
- YouTube Data API, Upload guide (scope `youtube.upload`): https://developers.google.com/youtube/v3/guides/uploading_a_video
- YouTube Analytics `reports.query` (scope `yt-analytics.readonly` / `yt-analytics-monetary.readonly`): https://developers.google.com/youtube/analytics/reference/reports/query
- YouTube OAuth scopes overview: https://developers.google.com/identity/protocols/oauth2/scopes
- TikTok Content Posting API (wymagany `video.publish`): https://developers.tiktok.com/doc/content-posting-api-get-started/
- TikTok OAuth scopes overview (`user.info.basic` przykładowy scope): https://developers.tiktok.com/doc/login-kit-manage-user-access-tokens
