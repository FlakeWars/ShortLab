# Wskazowki do generowania skryptow GDScript (Godot 4.6)

Ten dokument zbiera nauczki z iteracyjnych poprawek na przykladzie `bouncing_gap.gd`.
Docelowo jego tresc ma byc czescia prompta.

## 1) Geometria i rozmiary
- Opieraj rozmiary o realny viewport (np. `get_viewport().get_visible_rect().size`), a nie stale.
- Pilnuj, aby elementy miescily sie w kadrze (np. promien obreczy = `min(w, h) * 0.25`).
- W razie renderu Movie Maker weryfikuj, czy nie zaszla zmiana orientacji kadru.

## 2) Fizyka i kolizje
- Dla obreczy z przerwa **nie uzywaj pojedynczego `CollisionPolygon2D`** — to powoduje kolizje w szczelinie.
- Lepszy wzorzec: **dwa luki** + **segmenty** (`SegmentShape2D`) zamiast pelnego poligonu.
- Ustaw materialy fizyczne jawnie:
  - `bounce` wysoko (np. 0.98–1.0) dla zywych odbic,
  - `friction` = 0, `linear_damp` = 0, `angular_damp` = 0 dla braku sztucznego gaszenia.
- Dla obiektu poruszanego manualnie uzyj `AnimatableBody2D` + `sync_to_physics = true`.

## 3) Ruch i render
- Ruch obiektow aktualizuj w `_physics_process`, nie tylko w `_process`.
- Gdy rysujesz w `_draw()`, zawsze wywoluj `queue_redraw()` w ticku.
- Przy renderze offline preferuj **sekwencje PNG** i skladanie w ffmpeg, aby uniknac "zamrozonego" wideo.

## 4) Spawn i dynamika
- Wzrost liczby obiektow steruj przez **target count** (np. gdy obiekty wypadaja, zwieksz target).
- Spawnuj brakujace obiekty stopniowo (np. po 2 na klatke), zamiast "teleportowac" calej puli.

## 5) Stabilnosc i limity
- Pamietaj o limicie obiektow (`GODOT_MAX_NODES`). Przy wzroscie liczby obiektow ustaw wyzszy limit.
- Nie uzywaj IO ani assetow zewnetrznych (tekstury, fonty, audio) w v0.

## 6) Typy w GDScript
- Unikaj niejawnego `Variant` — dodawaj typy, gdy pojawiaja sie warningi (`var x: float = ...`).
- W pipeline walidacji warningi sa traktowane jak bledy — jawne typy minimalizuja problemy.

## 7) Kontrola czasu
- Zawsze respektuj limit czasu animacji (<= 60s).
- W renderze offline mozna zwiekszyc dokladnosc fizyki kosztem czasu:
  - `physics_fps` (np. 480),
  - `solver/default_iterations` (np. 32).

## 8) Antywzorzec: warianty tej samej animacji
- **Zakaz tworzenia wariantow** tej samej animacji (zmiana koloru/rozmiaru/parametru to nadal ta sama animacja).
- Cel: **maksymalna roznorodnosc idei**, a nie parametryzacja jednego schematu.
- Embedding ma zapobiegac powtorkom — ten przyklad nie moze sie pojawic ponownie w innym wariancie.
