# Operator Flow v2 (single-video cadence)

Data opracowania: 2026-03-24
Status: plan wykonawczy do realizacji etapami

## 1) Cel operacyjny
- Główny use-case: 1 film co 1-2 dni, nie batch N pomysłów.
- Priorytet: prosty, sekwencyjny flow i minimalna liczba decyzji na krok.
- Zasada: jeśli krok nie przechodzi, zatrzymujemy flow i naprawiamy tylko ten krok.

## 2) Docelowy flow (kanoniczny)
1. Pomysł:
   - Akcja A: wygeneruj 1 nowy pomysł.
   - Akcja B: wylosuj 1 pomysł z półki (`later`).
   - Decyzja: `accept` / `later` / `trash`.
2. Animacja (idea -> script -> validate -> estimate -> preview -> final):
   - System musi wykazać realizację założenia pomysłu przed finalizacją czasu.
   - Czas symulacji jest dobierany do momentu realizacji idei, potem skalowany do docelowego runtime (np. 60s).
3. Postprodukcja:
   - Dodanie krótkiego tekstu intro (hook) i/lub zasad animacji.
   - Dodanie audio (SFX + opcjonalny music bed).
4. QC:
   - Ocena jakości i zgodności z pomysłem.
   - Decyzja: `accepted` / `regenerate` / `rejected`.
5. Publikacja:
   - YouTube / TikTok (auto jeśli API gotowe, fallback manual_confirmed).
6. Metryki i analiza:
   - Snapshot 24h/72h/7d + rolling 14d.
   - Wnioski do następnego filmu.

## 3) Minimalny UX operatora (bez przeładowania)
- Widok 1: `Today` (jedna karta "co teraz").
- Widok 2: `Flow` (jeden aktywny krok, poprzednie zwinięte).
- Widok 3: `Library` (ideas: later/trash/published).
- Widok 4: `Insights` (metryki i trend po publikacji).

Wymagania UX:
- Domyślnie 1 pomysł, nie N.
- Brak sekcji legacy DSL w domyślnym widoku.
- Każdy krok ma jasny status: `todo | running | blocked | done`.
- Jeden główny CTA na ekran.

## 4) Kontrakt jakości treści (film)

### 4.1 Jakość animacji
- "Kiepski filmik" jest adresowany przez QC, ale część kryteriów musi być automatyczna:
  - czytelny ruch głównego obiektu,
  - brak pustych segmentów > X sekund,
  - spójność z ideą (intent coverage >= próg).

### 4.2 Tekst intro
- Krótki overlay na początku: 1-2 linie, 1.0-2.0 s, max 90 znaków.
- Cel: wyjaśnić "co widzę" lub "jaką zasadę oglądam".
- Tekst nie może zasłaniać kluczowego obiektu.

### 4.3 Audio
- SFX z events timeline (kolizje/spawn/merge/split).
- Tło muzyczne opcjonalne (poziom loudness kontrolowany).
- Standard normalizacji: LUFS docelowe dla short video.

## 5) Model danych i stany (v2)

### 5.1 Idea lifecycle
- `new` -> `accepted_for_production` -> `produced`.
- Poboczne: `later`, `trash`.

### 5.2 Animation lifecycle
- `script_compiled` -> `validated` -> `preview_ready` -> `render_ready` -> `rendered` -> `audio_text_ready` -> `qc_*` -> `published` -> `metrics`.

### 5.3 Nowe byty
- `intro_overlay_template` + `intro_overlay_instance`.
- `audio_track` + `audio_mix_job`.
- `intent_check_report` (czy animacja realizuje pomysł i kiedy).

## 6) Implementacja etapowa (wykonawcza)

### Etap A - UX reset pod 1 film
- Dodać tryb "single-video cadence" jako domyślny.
- Ukryć/hard-collapse elementy legacy i nadmiarowe panele.
- Wdrożyć ekran `Today` + aktywny krok flow.

DoD:
- Operator przechodzi od pomysłu do renderu bez skakania po zakładkach.
- Brak konieczności generowania N pomysłów.

### Etap B - Intent coverage + duration scaling
- Dodać `intent_check` po preview.
- Jeśli idea realizuje się późno, zwiększyć czas symulacji i przeskalować final do target runtime.
- Zapisać raport czasu realizacji idei.

DoD:
- API zwraca `intent_reached_at_s`, `recommended_sim_duration_s`, `target_runtime_s`, `speed_factor`.

### Etap C - Intro text module
- Generator krótkiego tekstu (LLM + limit znaków + walidacja).
- Render overlay przez FFmpeg (lub Godot layer) jako osobny krok.
- Presety pozycji/stylu (bez ręcznego projektowania).

DoD:
- `POST /ops/overlay/intro` tworzy artefakt i metadata.

### Etap D - Audio module
- Zdarzenia audio z timeline + mapowanie do biblioteki SFX.
- Opcjonalny music bed i miks końcowy.
- Kontrola głośności i clipping.

DoD:
- `POST /ops/audio/mix` tworzy finalny artefakt A/V.

### Etap E - QC i publish hardening
- Rozszerzyć QC o kryteria: intent coverage, intro readability, audio quality.
- Publish connectors: YouTube + TikTok (manual fallback utrzymany).

DoD:
- Przy `accepted` można publikować bez kroków bocznych.

### Etap F - Metrics & insight loop
- Pull metryk i dashboard 24h/72h/7d/14d.
- Prosty raport "what worked" per video.

DoD:
- `Insights` pokazuje porównanie ostatnich publikacji i rekomendację dla kolejnego filmu.

## 7) Integracje API i MCP (stan + decyzje)

### 7.1 YouTube
- Upload: YouTube Data API `videos.insert`.
- Metryki: YouTube Analytics API `reports.query`.
- Źródła oficjalne:
  - https://developers.google.com/youtube/v3/docs/videos/insert
  - https://developers.google.com/youtube/analytics/reference/reports/query

### 7.2 TikTok
- Publish: Content Posting API (`video.publish` / `video.upload`).
- Ograniczenia: audyt klienta i limity requestów.
- Display/odczyt video metadata: Display API (`video.list`).
- Źródła oficjalne:
  - https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
  - https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
  - https://developers.tiktok.com/doc/display-api-overview

### 7.3 MCP server discovery
- Katalog referencyjny: https://github.com/modelcontextprotocol/servers
- Registry: https://registry.modelcontextprotocol.io/
- Zweryfikowane wpisy w Official MCP Registry (stan na 2026-03-24):
  - `io.github.wmarceau/youtube-creator` (opis: upload Shorts/videos + analytics, pakiet `youtube-creator-mcp`)
  - `io.github.wmarceau/tiktok-creator` (opis: post videos + analytics, pakiet `tiktok-creator-mcp`)
  - `io.github.kirbah/mcp-youtube` (YouTube Data API read/search, token-optimized data)
  - `io.github.jkawamoto/mcp-youtube-transcript` (transcripts, read-only)
- Dodatkowo poza Registry: `fmd-labs/viral-app-mcp` (hostowany zdalnie, model kredytowy; read analytics TikTok, bez publish).

Wniosek po przeglądzie:
- Dostępne MCP-y są użyteczne dla research/insights, ale dla krytycznego flow publikacji wymagają dodatkowego audytu (w tym: source repo, licencja, utrzymanie, token handling, ToS platform).

Decyzja architektoniczna:
- Core publish/metrics zostaje na oficjalnych API platform.
- MCP używamy jako warstwę wspierającą (insights/assist), nie jako jedyne źródło krytycznego publish flow.

Plan wdrożeniowy MCP (bez łamania krytycznego flow):
1. Etap `assist-only`:
   - podłączyć 1 read-only MCP do benchmarków trendów i transcriptów (bez upload/publish),
   - wyniki zapisywać jako pomocniczy kontekst QC/insights, bez wpływu na status publikacji.
2. Etap `creator MCP trial`:
   - uruchomić trial `youtube-creator`/`tiktok-creator` tylko w środowisku testowym,
   - porównać skuteczność i stabilność z natywnymi endpointami API.
3. Gate produkcyjny:
   - wymagany pozytywny audyt bezpieczeństwa i compliance ToS,
   - fallback `manual_confirmed` musi pozostać aktywny.

Stan implementacji gate (2026-03-24):
- `make mcp-publish-audit`:
  - audyt registry/repo/license/utrzymania/env-contract,
  - raport JSON/MD w `out/reports`.
- `make publish-oauth-smoke`:
  - smoke OAuth refresh (offline/online) dla YouTube/TikTok,
  - policy gate (`OAUTH_SMOKE_REQUIRE`).
- `make mcp-compliance-check`:
  - formalna checklista compliance (`docs/mcp-compliance-checklist.json`) + walidator strict.

## 8) Porządkowanie i usuwanie "nietrafionych" elementów
- Idea `trash` jest terminalna (domyślnie ukryta w UI, opcjonalny auto-delete po TTL).
- `later` ma limit wieku; po TTL trafia do review lub cleanup.
- Zasada repo: nie utrzymujemy martwych paneli i feature flag bez właściciela.

## 9) Kryteria gotowości projektu (quality gate)
- Operator wykonuje pełny flow bez CLI.
- Czas obsługi jednego filmu <= 15 min pracy operatora (bez czasu renderu).
- Każdy film ma: `idea linkage`, `intent report`, `intro`, `audio`, `qc`, `publish record`, `metrics snapshot`.

## 10) Braki do doprecyzowania (wymagają decyzji)
1. Docelowy runtime filmu:
   - decyzja: domyślnie `60s` dla wszystkich platform,
   - wyjątek: operator może ustawić override runtime dla konkretnego filmu, jeśli scaling do 60s daje nienaturalny efekt.
2. Język intro overlay:
   - decyzja: domyślnie `EN` (maksymalizacja potencjalnego zasięgu).
3. Polityka `trash`:
   - decyzja: hard-delete natychmiast po oznaczeniu idei jako `trash`.
