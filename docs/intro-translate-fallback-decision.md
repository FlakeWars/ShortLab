# Intro Translate Fallback Decision (v2)

Data: 2026-03-24  
Zakres: fallback dla EN tłumaczenia intro overlay (`intro_translate`).

## Decyzja
W v2 **nie dodajemy osobnego offline translatora** jako drugiego fallbacku.

## Uzasadnienie
- Aktualny fallback sanitizacyjny (`_sanitize_intro_text`) jest deterministyczny, szybki i bez dodatkowych zależności.
- Dodanie offline translatora zwiększałoby złożoność utrzymania (modele/binarki, kompatybilność, jakość na krótkich tekstach), a projekt ma restrykcję stabilności wersji (`versions.env`).
- Intro overlay to bardzo krótki tekst; dla fail-safe wystarcza bezpieczna sanitizacja + mapowanie prefiksów PL.

## Konsekwencje
- Gdy LLM tłumaczenia jest niedostępny/błędny, system zachowuje ciągłość przez fallback sanitizacyjny.
- Jakość EN w fallbacku może być mniej naturalna niż przy LLM.

## Kryteria rewizji decyzji
Wracamy do tematu offline fallback, gdy jednocześnie:
1. częstość fallbacku > 10% requestów `intro_translate` w oknie 14 dni, oraz
2. operator zgłasza istotną degradację jakości EN dla publikacji.

## Powiązane konfiguracje
- `INTRO_EN_TRANSLATE_ENABLED=1|0`
- `LLM_TASK_PROFILE_INTRO_TRANSLATE`
- `LLM_ROUTE_INTRO_TRANSLATE_*`
