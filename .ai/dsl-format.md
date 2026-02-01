# Wybór formatu DSL (v1)

## Decyzja
**Wybieramy YAML jako format wejściowy DSL v1**, z możliwością konwersji do JSON w narzędziach (np. na etapie walidacji).

## Uzasadnienie
- **Czytelność dla człowieka**: łatwiej pisać i recenzować specyfikacje (wiele zagnieżdżeń, listy, reguły).
- **Mniej szumu**: brak nawiasów i przecinków ułatwia iterację na pomysłach i szkicach.
- **Zgodność z przykładowymi DSL**: już stworzone przykłady są w YAML.

## Konsekwencje
- Parser i walidacja muszą obsługiwać YAML.
- Dla stabilności pipeline’u możemy w przyszłości trzymać wewnętrznie JSON (np. po normalizacji).
