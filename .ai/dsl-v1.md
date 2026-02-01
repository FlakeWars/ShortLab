# DSL v1 — szkic specyfikacji (struktura i pola)

Dokument opisuje minimalny zakres DSL dla animacji Short (MVP). Format docelowy: **YAML** (z możliwością konwersji do JSON). Specyfikacja jest deterministyczna i wersjonowana.

## 1. Struktura pliku

```text
root
├─ dsl_version (required, string)
├─ meta (required, object)
├─ scene (required, object)
├─ systems (required, object)
├─ termination (required, object)
├─ output (required, object)
└─ notes (optional, string)
```

## 2. Pola wymagane

### 2.1. dsl_version
- Typ: string
- Przykład: "1.0"
- Cel: wersjonowanie DSL i kompatybilność wsteczna.

### 2.2. meta
- Typ: object
- Wymagane pola:
  - `id` (string, unikalny identyfikator animacji/specyfikacji)
  - `title` (string, krótki tytuł)
  - `seed` (integer, deterministyczne RNG)
  - `tags` (array of string, min. 0)

### 2.3. scene
- Typ: object
- Wymagane pola:
  - `canvas` (object)
    - `width` (integer)
    - `height` (integer)
    - `fps` (integer)
    - `duration_s` (number)
  - `palette` (array of color tokens, np. hex "#RRGGBB")
  - `background` (color token)

### 2.4. systems
Minimalny zestaw systemów, które opisują reguły animacji.
- Typ: object
- Wymagane pola:
  - `entities` (array)
    - definicje typów obiektów (patrz 3.1)
  - `spawns` (array)
    - definicje inicjalizacji obiektów (patrz 3.2)
  - `rules` (array)
    - reguły zachowania i interakcji (patrz 3.3)

### 2.5. termination
- Typ: object
- Wymagane pola (jedno z):
  - `time` (object): zakończ po czasie
    - `at_s` (number)
  - `condition` (object): warunek logiczny
    - `type` (string, np. "population", "coverage", "entropy")
    - `params` (object)

### 2.6. output
- Typ: object
- Wymagane pola:
  - `format` (string, np. "mp4")
  - `resolution` (string, np. "1080x1920")
  - `codec` (string, np. "h264")
  - `bitrate` (string, np. "8M")

## 3. Elementy systemu (wymagane typy)

### 3.1. entities (definicje typów)
Każdy typ obiektu opisuje właściwości i zasady renderu.
Minimalne pola:
- `id` (string)
- `shape` (string: "circle" | "square" | "line" | "triangle" | "custom")
- `size` (number or object)
- `color` (token z palette)
- `mass` (number, opcjonalne, default=1)
- `render` (object, opcjonalne: np. stroke, opacity)

### 3.2. spawns (inicjalizacja)
Jak obiekty pojawiają się na starcie.
Minimalne pola:
- `entity_id` (string)
- `count` (integer)
- `distribution` (object, np. "random", "grid", "orbit")
- `params` (object)

### 3.3. rules (reguły zachowania)
Lista reguł uruchamianych w pętli symulacji.
Minimalne pola:
- `id` (string)
- `type` (string, np. "move", "orbit", "attract", "repel", "split", "merge", "decay", "memory")
- `applies_to` (selector: entity_id lub tag)
- `params` (object)
- `probability` (number 0..1, optional)

## 4. Pola opcjonalne (zalecane)

### 4.1. scene.time
Ustawienia czasu (np. skala symulacji).
- `timescale` (number, default=1.0)

### 4.2. systems.fsm
Prosty FSM dla globalnego stanu animacji.
- `states` (array of string) — lista stanów
- `initial` (string) — stan początkowy, musi należeć do `states`
- `transitions` (array of object)
  - `from` (string)
  - `to` (string)
  - `when` (object) — warunek przejścia (jeden z typów)
    - `type` (string: "time" | "event" | "metric")
    - `params` (object)
      - `time`: { `at_s` (number) }
      - `event`: { `name` (string), `count` (integer, optional) }
      - `metric`: { `name` (string), `op` (string: ">" | ">=" | "<" | "<=" | "==" ), `value` (number) }
  - `once` (boolean, optional, default=true)
  - `priority` (integer, optional, default=0; wyższa = wcześniejsza)

### 4.3. systems.forces
Globalne siły (np. grawitacja).
- `gravity` (vector or number)
- `noise` (object)

### 4.4. systems.interactions
Złożone interakcje między typami obiektów.
- `pairs` (array of {a, b, rule})

### 4.5. meta.attribution
Źródło pomysłu / autor.

## 5. Walidacja i zgodność
- Każdy plik musi mieć `dsl_version`.
- Wszystkie `entity_id` w spawns/rules muszą istnieć w `entities`.
- `seed` jest wymagany do deterministyczności.
- `termination` musi być jednoznaczne (time albo condition).
- `systems.fsm` (jeśli występuje): wszystkie `from/to` muszą istnieć w `states`.

## 6. Przykładowe końce (termination.type)
- `population`: gdy liczba obiektów == N
- `coverage`: gdy wypełnienie ekranu > X%
- `entropy`: gdy liczba obiektów > limit
- `stability`: gdy brak zmian przez T sekund
