# Conventional Commits – reguły w projekcie

Dokument oparty o specyfikację Conventional Commits 1.0.0.

## Format wiadomości
```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Wymagania minimalne
- Wiadomość commita musi zaczynać się od typu zakończonego `:` i spacją.
- `feat` oznacza nową funkcjonalność.
- `fix` oznacza poprawkę błędu.
- Zakres (scope) jest opcjonalny i zapisany w nawiasach, np. `feat(api): ...`.
- Opis jest wymagany i następuje bezpośrednio po prefiksie.

## Breaking changes
- Breaking change oznaczamy **albo** `!` w nagłówku, **albo** stopką `BREAKING CHANGE:`.
- Jeśli używasz `!`, stopka `BREAKING CHANGE` jest opcjonalna.

## Dodatkowe typy
Specyfikacja dopuszcza typy inne niż `feat` i `fix` (np. `docs`, `refactor`, `test`, `ci`, `build`, `chore`), ale nie narzuca ich listy.

## Przykłady
```
feat(api): add metrics pull endpoint
fix(renderer)!: correct RNG seeding

docs: update setup instructions

chore: bump tool versions
```
