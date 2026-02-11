# Kontrakt GDScript (Godot 4.6) - v0

Ten dokument opisuje minimalny kontrakt dla skryptow GDScript generowanych przez LLM.
Cel: szybki, stabilny render 2D z fizyka przy minimalnej liczbie bledow.

## 1) Wersja i kompatybilnosc
- Docelowa wersja silnika: **Godot 4.6.x**.
- Zakaz API z Godot 3.x (inne nazwy klas i metod).

## 2) Dozwolone node'y (podstawowa pula)
- `Node2D` (root sceny)
- `RigidBody2D` (dynamiczne obiekty fizyczne)
- `AnimatableBody2D` (obiekty poruszane manualnie, wplywajace na fizyke)
- `StaticBody2D` (statyczne przeszkody)
- `CollisionShape2D`

## 3) Dozwolone ksztalty (CollisionShape2D)
- `CircleShape2D`
- `RectangleShape2D`
- `PolygonShape2D` (dla wycinkow/obreczy)

## 4) Zasady skryptu
- Skrypt musi byc kompletny i dzialac bez dodatkowych plikow.
- Skrypt nie moze wykonywac IO (plikow/sieci) poza katalogiem projektu.
- Skrypt musi miec wyrazny punkt startu (np. `_ready()`).
- Czas animacji: **maks. 60s**.
- Limit obiektow aktywnych: **max 200** (soft limit).
- Brak assetow zewnetrznych (tekstury, fonty, audio) w v0.

## 5) Format wyjscia LLM
LLM zwraca **pelny kod GDScript** (jeden plik `.gd`), bez komentarzy opisowych.

## 6) Walidacja (smoke test)
Minimalna walidacja obejmuje:
- parse skryptu,
- load sceny,
- krotki tick fizyki (1-2s).

## 7) Kontrakt bledow dla petli naprawy
W przypadku bledow walidacji raport musi miec strukture:

```json
{
  "errors": [
    {
      "path": "RigidBody2D.mass",
      "expected": "number > 0",
      "got": "null",
      "message": "missing required property"
    }
  ]
}
```

## 8) Retry policy (LLM repair)
- Max prob: 3.
- Po przekroczeniu limitu: odrzut kandydata albo nowa generacja.
  - Fallback: zapisac raport bledow i oznaczyc kandydata jako `invalid`.
