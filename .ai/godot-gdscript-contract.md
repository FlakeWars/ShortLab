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
- `SegmentShape2D` (dla lukow/odcinkow)

## 3.1) Dozwolone zasoby
- `PhysicsMaterial`

## 4) Zasady skryptu
- Skrypt musi byc kompletny i dzialac bez dodatkowych plikow.
- Skrypt nie moze wykonywac IO (plikow/sieci) poza katalogiem projektu.
- Skrypt musi miec wyrazny punkt startu (np. `_ready()`).
- Czas animacji: **maks. 60s**.
- Limit obiektow aktywnych: **max 200** (soft limit).
- Brak assetow zewnetrznych (tekstury, fonty, audio) w v0.
- Zakaz generowania wariantow tej samej animacji (zmiany parametrow nie tworza nowej idei).

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

## 9) Przyklad referencyjny (opis + wynik GDScript)

### Oczekiwany opis animacji
- Na ekranie widoczny jest okrag z przerwa (szczelina) ok. 40 stopni.
- Okrag obraca sie zgodnie z ruchem wskazowek zegara wokol srodka.
- Dziala grawitacja w dol ekranu.
- W srodku pojawiaja sie male kulki, odbijaja sie od obreczy zgodnie z fizyka.
- Gdy kulka wypadnie przez szczeline, znika; w jej miejsce pojawiaja sie nowe kulki.
- Liczba kulek z czasem rosnie (do limitu), animacja trwa maks. 60s.

### Wynik GDScript (pelny plik .gd)
```gdscript
extends Node2D

const RADIUS := 18.0
const GRAVITY := 980.0
const BALL_RESTITUTION := 0.98
const BALL_FRICTION := 0.0
const RING_RESTITUTION := 1.0
const RING_FRICTION := 0.0
const RING_SIZE_FACTOR := 0.25
const GAP_DEG := 40.0
const ROT_SPEED := 0.6
const MAX_BALLS := 120
const PAIR_SPAWN := 2
const MIN_BALLS := 2

var ring_body
var ring_shapes := []
var viewport_size := Vector2.ZERO
var ring_radius := 0.0
var ring_points := PackedVector2Array()
var ring_points_secondary := PackedVector2Array()
var elapsed_s := 0.0
var target_balls: int = MIN_BALLS


func _ready() -> void:
    set_process(true)
    set_physics_process(true)
    viewport_size = _resolve_viewport_size()
    _setup_physics()
    _update_ring_geometry()
    _spawn_balls(MIN_BALLS)
    queue_redraw()


func _setup_physics() -> void:
    PhysicsServer2D.area_set_param(
        get_world_2d().space,
        PhysicsServer2D.AREA_PARAM_GRAVITY,
        GRAVITY
    )
    ring_body = AnimatableBody2D.new()
    ring_shapes.clear()
    ring_body.position = viewport_size * 0.5
    ring_body.sync_to_physics = true
    ring_body.physics_material_override = PhysicsMaterial.new()
    ring_body.physics_material_override.bounce = RING_RESTITUTION
    ring_body.physics_material_override.friction = RING_FRICTION
    add_child(ring_body)


func _physics_process(delta: float) -> void:
    elapsed_s += delta
    var current_size := _resolve_viewport_size()
    if current_size != viewport_size:
        viewport_size = current_size
        ring_body.position = viewport_size * 0.5
        _update_ring_geometry()
    ring_body.position = viewport_size * 0.5
    ring_body.rotation += ROT_SPEED * delta
    var removed: int = _cleanup_outside()
    if removed > 0:
        target_balls = min(MAX_BALLS, target_balls + removed)
    _spawn_missing()
    queue_redraw()


func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, viewport_size), Color(0, 0, 0), true)
    draw_circle(viewport_size * 0.5, 6.0, Color(1, 1, 1))
    _draw_ring()
    _draw_balls()


func _draw_ring() -> void:
    if ring_points.is_empty():
        return
    var center = ring_body.position
    var rotated := PackedVector2Array()
    for point in ring_points:
        rotated.append(point.rotated(ring_body.rotation) + center)
    draw_polyline(rotated, Color(0.9, 0.9, 0.9), 4.0, true)
    if not ring_points_secondary.is_empty():
        var rotated_secondary := PackedVector2Array()
        for point in ring_points_secondary:
            rotated_secondary.append(point.rotated(ring_body.rotation) + center)
        draw_polyline(rotated_secondary, Color(0.9, 0.9, 0.9), 4.0, true)


func _draw_balls() -> void:
    for child in get_children():
        if child is RigidBody2D:
            draw_circle(child.position, RADIUS, Color(0.4, 0.8, 1.0))


func _spawn_missing() -> void:
    var missing: int = target_balls - _ball_count()
    if missing <= 0:
        return
    _spawn_balls(min(missing, PAIR_SPAWN))


func _spawn_balls(count: int) -> void:
    if _ball_count() >= MAX_BALLS or count <= 0:
        return
    var center := viewport_size * 0.5
    var offset := Vector2(0.0, -ring_radius * 0.1)
    var spawn_count: int = min(count, MAX_BALLS - _ball_count())
    for i in range(spawn_count):
        var ball := RigidBody2D.new()
        ball.gravity_scale = 1.0
        ball.linear_velocity = Vector2.ZERO
        ball.linear_damp = 0.0
        ball.angular_damp = 0.0
        var x_offset: float = (float(i) - (spawn_count - 1) * 0.5) * RADIUS * 2.0
        ball.position = center + offset + Vector2(x_offset, 0.0)
        var shape := CollisionShape2D.new()
        var circle := CircleShape2D.new()
        circle.radius = RADIUS
        shape.shape = circle
        ball.add_child(shape)
        ball.physics_material_override = PhysicsMaterial.new()
        ball.physics_material_override.bounce = BALL_RESTITUTION
        ball.physics_material_override.friction = BALL_FRICTION
        add_child(ball)


func _cleanup_outside() -> int:
    var removed: int = 0
    for child in get_children():
        if child is RigidBody2D:
            if (
                child.position.y > viewport_size.y + 200
                or child.position.x < -200
                or child.position.x > viewport_size.x + 200
            ):
                child.queue_free()
                removed += 1
    if _ball_count() == 0:
        target_balls = MIN_BALLS
        _spawn_balls(MIN_BALLS)
    return removed


func _ball_count() -> int:
    var count := 0
    for child in get_children():
        if child is RigidBody2D:
            count += 1
    return count


func _build_ring_with_gap(
    radius: float, gap_deg: float, segments: int, second_arc: bool
) -> PackedVector2Array:
    var points := PackedVector2Array()
    var gap_rad: float = deg_to_rad(gap_deg)
    var start: float = gap_rad * 0.5
    var end: float = TAU - gap_rad * 0.5
    var mid: float = lerp(start, end, 0.5)
    var arc_start: float = start
    var arc_end: float = mid
    if second_arc:
        arc_start = mid
        arc_end = end
    for i in range(segments + 1):
        var t := float(i) / float(segments)
        var angle: float = arc_start + (arc_end - arc_start) * t
        points.append(Vector2(cos(angle), sin(angle)) * radius)
    return points


func _update_ring_geometry() -> void:
    ring_radius = max(min(viewport_size.x, viewport_size.y) * RING_SIZE_FACTOR, 50.0)
    ring_points = _build_ring_with_gap(ring_radius, GAP_DEG, 64, false)
    ring_points_secondary = _build_ring_with_gap(ring_radius, GAP_DEG, 64, true)
    for shape in ring_shapes:
        shape.queue_free()
    ring_shapes.clear()
    _add_segment_shapes(ring_points)
    _add_segment_shapes(ring_points_secondary)


func _add_segment_shapes(points: PackedVector2Array) -> void:
    if points.size() < 2:
        return
    for i in range(points.size() - 1):
        var segment := SegmentShape2D.new()
        segment.a = points[i]
        segment.b = points[i + 1]
        var collision := CollisionShape2D.new()
        collision.shape = segment
        ring_body.add_child(collision)
        ring_shapes.append(collision)


func _resolve_viewport_size() -> Vector2:
    var size := get_viewport().get_visible_rect().size
    if size.x > 0.0 and size.y > 0.0:
        return size
    var width := float(ProjectSettings.get_setting("display/window/size/viewport_width", 1080))
    var height := float(ProjectSettings.get_setting("display/window/size/viewport_height", 1920))
    return Vector2(width, height)
```
