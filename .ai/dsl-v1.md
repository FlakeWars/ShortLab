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
- `background` (color token, **musi być elementem `palette`**)

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
    - `type` (string: "metric")
    - `params` (object)

### 2.6. output
- Typ: object
- Wymagane pola:
  - `format` (string, v1.1: "mp4")
  - `resolution` (string, np. "1080x1920")
  - `codec` (string, v1.1: "h264")
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

#### 3.1.1. entities.tags (v1.1)
Opcjonalne pole `tags` pozwala grupować encje.
- `tags` (array of string)

Zasady:
- `tag:<name>` w selectorach musi odnosić się do tagu zdefiniowanego w `entities.tags`.

#### 3.1.2. entities.size (v1.1)
`size` może być:
- number (stały rozmiar w `px`)
- object **(wymaga `min` i `max`)**:
  - `min` (number, px)
  - `max` (number, px)
  - `distribution` (string: "uniform" | "normal", optional)

#### 3.1.3. entities.render (v1.1)
Dozwolone pola:
- `stroke` (object)
  - `width` (number, px)
  - `color` (color token)
- `opacity` (number 0..1)

### 3.2. spawns (inicjalizacja)
Jak obiekty pojawiają się na starcie.
Minimalne pola:
- `entity_id` (string)
- `count` (integer)
- `distribution` (object: `type` + opcjonalne `params`)

#### 3.2.2. Słownik dystrybucji spawnu/emiterów (v1.1)
`distribution.type`:
- `center` — punkt środka ekranu
  - params: **brak** (nie podawaj pustego `params`)
- `random` — losowy punkt w obszarze
  - params: `padding` (number, optional)
- `grid` — siatka
  - params: **wymagane** `cols` (integer), `rows` (integer)
- `orbit` — punkt na okręgu
  - params: **wymagane** `radius` (number), `speed` (number, optional)

#### 3.2.1. Emitery / spawny w czasie (v1.1)
Dodatkowa sekcja `emitters` w `systems` opisuje spawny w czasie.

Struktura:
- `emitters` (array)
  - `id` (string)
  - `entity_id` (string)
  - `rate_per_s` (number) — średnia liczba obiektów na sekundę
  - `distribution` (object; jak w `spawns`)
  - `params` (object, optional) — **opcjonalne tylko dla emitera**
  - `start_s` (number, optional, default=0)
  - `end_s` (number, optional) — jeśli brak, emituje do końca
- `limit` (integer, optional) — maksymalna liczba obiektów z emitera

Uwaga: `limit` dotyczy **pojedynczego emitera** (per-emitter), a nie globalnej liczby obiektów.

### 3.3. rules (reguły zachowania)
Lista reguł uruchamianych w pętli symulacji.
Minimalne pola:
- `id` (string)
- `type` (string, np. "move", "orbit", "attract", "repel", "split", "merge", "decay", "memory")
- `applies_to` (selector: entity_id lub tag)
- `params` (object)
- `probability` (number 0..1, optional)

#### 3.3.1. Słownik reguł `rules.type` + wymagane `params` (v1.1)
Poniższa lista definiuje **minimalne, wymagane parametry** dla każdej reguły.
Parametry opcjonalne mogą mieć wartości domyślne ustalone przez renderer.

- `move`
  - wymagane: `speed` (number)
  - opcjonalne: `direction` (vector2, default: `[1.0, 0.0]`)
- `orbit`
  - wymagane: `center` (selector lub point), `speed` (number)
  - opcjonalne: `radius` (number; gdy brak, użyj bieżącej odległości)
- `attract`
  - wymagane: `target` (selector lub point), `strength` (number)
  - opcjonalne: `radius` (number), `falloff` (string: "linear" | "inverse_square")
- `repel`
  - wymagane: `target` (selector lub point), `strength` (number)
  - opcjonalne: `radius` (number), `falloff` (string: "linear" | "inverse_square")
- `split`
  - wymagane: `into` (integer), `angle_threshold_deg` (number)
  - opcjonalne: `speed_multiplier` (number, default=1.0)
- `merge`
  - wymagane: `distance` (number)
  - opcjonalne: `mode` (string: "largest" | "average", default="largest")
- `decay`
  - wymagane: `rate_per_s` (number 0..1)
- `memory`
  - wymagane: `decay` (number 0..1), `influence` (number)

#### 3.3.2. Selektory (v1.1)
`selector` wskazuje zbiór obiektów. Dozwolone formy:
- `entity_id` (string) — np. `"particle"`
- `tag:<name>` — np. `"tag:debris"`
- `"*"` lub `"all"` — wszystkie obiekty

Zasady:
- `applies_to`, `center`, `target`, `a`, `b` mogą używać selectorów.
- Jeśli selector wskazuje wiele obiektów, renderer wybiera:
  - dla `center/target`: **najbliższy** obiekt względem obiektu, do którego reguła się odnosi
  - dla `a/b`: wszystkie pary typu A-B

## 4. Pola opcjonalne (zalecane)

### 4.1. scene.time
Ustawienia czasu (np. skala symulacji).
- `timescale` (number, default=1.0)

### 4.1.1. Jednostki i układ współrzędnych (v1.1)
- **Układ współrzędnych**: punkt (0,0) w lewym górnym rogu, oś X w prawo, oś Y w dół.
- **Jednostki przestrzeni**: wszystkie pozycje i rozmiary w pikselach ekranu (`px`).
- **Jednostki czasu**: `duration_s`, `at_s` i parametry prędkości są w sekundach (`s`).
- **Prędkość**: wyrażona w `px/s`.

## 5. Częste błędy (do unikania)
- **`entities.size` jako obiekt bez `min` i `max`** → niepoprawne.
- **`entities.size.value`** → nie jest obsługiwane (użyj liczby lub `{min,max}`).
- **`spawns.params` na poziomie spawnu** → nie istnieje; `params` są tylko w `distribution`.
- **`distribution.params: {}` dla `center`** → pomiń `params` w całości.
- **Kąty**: podawane w stopniach (`deg`), zgodnie z ruchem wskazówek zegara.
- **Wektory 2D**: `[x, y]` w `px` lub jednostkach bezwzględnych (bez normalizacji); jeśli wymagany kierunek, normalizacja odbywa się w rendererze.
- **Punkty (point)**: zapis jako obiekt `{ x: number, y: number }` w `px`.

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

#### 4.2.1. Ujednolicony kontrakt metryk (v1.1)
Zarówno `termination.condition` jak i `fsm.transitions.when` dla metryk używają tego samego kształtu:
- `type`: `"metric"`
- `params`:
  - `name` (string: "population" | "coverage" | "entropy" | "stability")
  - `op` (string)
  - `value` (number)
  - `window_s` (number, optional)
  - `sample_every_s` (number, optional)

W `termination.condition` `type` oznacza **rodzaj warunku**, więc dla metryk używamy:
```
termination:
  condition:
    type: "metric"
    params:
      name: "population"
      op: ">="
      value: 200
```
  - `once` (boolean, optional, default=true)
  - `priority` (integer, optional, default=0; wyższa = wcześniejsza)

### 4.3. systems.forces
Globalne siły (np. grawitacja).
- `gravity` (vector or number)
- `noise` (object)

#### 4.3.1. Słownik forces (v1.1)
- `gravity` (number lub vector2) — stała siła w `px/s^2`
- `noise` (object)
  - `strength` (number)
  - `scale` (number)
  - `seed` (integer, optional)

#### 4.3.2. Parametry forces (v1.1)
- `gravity`:
  - number: grawitacja w osi Y (wartość dodatnia = w dół)
  - vector2: `{ x: number, y: number }`
- `noise`:
  - `strength` (number, >= 0)
  - `scale` (number, > 0)
  - `seed` (integer, optional) — jeśli podany, szum jest **deterministyczny w czasie** (statyczny)

### 4.4. systems.interactions
Złożone interakcje między typami obiektów.
- `pairs` (array of {a, b, rule})

### 4.4.1. Model kolizji i interakcji (v1.1)
Minimalny model interakcji definiujemy w `systems.interactions`.

Struktura:
- `pairs` (array) — lista reguł par typów obiektów
  - `a` (selector) — typ A
  - `b` (selector) — typ B
  - `rule` (object)
    - `type` (string: "merge" | "split" | "repel" | "attract")
    - `params` (object) — wymagane parametry zgodne ze słownikiem reguł
    - `when` (object, optional)
      - `distance_lte` (number) — próg kolizji/oddziaływania w `px`
      - `probability` (number 0..1, optional)

Zasady:
- `a` i `b` mogą być `entity_id` albo `tag:...`.
- Jeżeli `when` nie podano, interakcja działa ciągle.
- Interakcje są wykonywane **po** regułach w kroku 4 (patrz kolejność ewaluacji).

### 4.4.2. Schemat `systems.interactions` (v1.1)
Każdy wpis w `pairs` musi mieć:
- `a` (selector)
- `b` (selector)
- `rule.type` (string: "merge" | "split" | "repel" | "attract")
- `rule.params` (zgodne ze słownikiem reguł)

### 4.5. meta.attribution
Źródło pomysłu / autor.

### 4.7. systems.constraints (v1.1)
Ograniczenia przestrzeni i reguły bounds.
- `bounds` (object)
  - `type` (string: "clamp" | "bounce" | "wrap")
  - `padding` (number, optional, default=0)
  - `restitution` (number 0..1, optional; tylko dla "bounce")

### 4.6. Kolejność ewaluacji systemów (v1.1)
Standardowa kolejność w jednej klatce:
1) **Spawn/init** (tylko start lub emitery; jeśli dotyczy).
2) **Forces** (globalne siły, np. grawitacja/noise).
3) **Rules** (kolejno według listy w DSL).
4) **Interactions/Collisions** (jeśli zdefiniowane).
5) **Constraints/Bounds** (np. odbicia od krawędzi, klamry pozycji).
6) **FSM transitions** (jeśli występują).
7) **Termination check** (warunki zakończenia).

Renderer może rozszerzać kroki 4–5, ale nie powinien zmieniać kolejności 1–3 bez zmiany wersji DSL.

#### 4.6.1. Interactions vs Constraints (v1.1)
- **Interactions/Collisions**: reguły zależne od relacji między obiektami (np. merge/split/repel/attract), wykonywane na parach obiektów lub grupach.
- **Constraints/Bounds**: reguły niezależne od relacji, dotyczące ograniczeń przestrzeni (np. odbicia od krawędzi, clamp pozycji).

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

### 6.1. Definicje metryk dla termination (v1.1)
Metryki są używane w `termination.condition` i w `fsm.transitions.when` (type=metric).

Wspólne parametry:
- `window_s` (number, optional) — okno czasowe do wygładzania
- `sample_every_s` (number, optional) — próbkowanie metryk

Metryki:
- `population` — liczba aktywnych obiektów
  - `params`: `value` (number), `op` (string: ">" | ">=" | "<" | "<=" | "==")
- `coverage` — procent pokrycia ekranu przez obiekty
  - Definicja: suma pól kół o promieniu `size` / pole ekranu (cap do 1.0)
  - `params`: `value` (number 0..1), `op` (string: ">" | ">=" | "<" | "<=" | "==")
- `entropy` — miara nieuporządkowania (np. liczba obiektów lub ich rozkład)
  - Definicja (v1.1): liczba obiektów (alias `population`)
  - `params`: `value` (number), `op` (string: ">" | ">=" | "<" | "<=" | "==")
- `stability` — brak zmian pozycji w czasie
  - Definicja: udział obiektów z prędkością <= `stability_eps` w oknie czasu
  - `params`: `value` (number 0..1), `op` (string: ">" | ">=" | "<" | "<=" | "=="), `window_s` (number), `stability_eps` (number, default=1e-3)
