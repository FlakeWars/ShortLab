extends Node2D

const WIDTH := 1080
const HEIGHT := 1920
const RADIUS := 18.0
const GRAVITY := 980.0
const BALL_RESTITUTION := 0.9
const RING_RADIUS := 300.0
const GAP_DEG := 40.0
const ROT_SPEED := 0.6
const MAX_BALLS := 120
const PAIR_SPAWN := 2

var ring_body
var ring_shape
var ring_points := PackedVector2Array()
var elapsed_s := 0.0


func _ready() -> void:
    set_process(true)
    set_physics_process(true)
    _setup_physics()
    _spawn_pair()
    queue_redraw()


func _setup_physics() -> void:
    PhysicsServer2D.area_set_param(
        get_world_2d().space,
        PhysicsServer2D.AREA_PARAM_GRAVITY,
        GRAVITY
    )
    ring_body = AnimatableBody2D.new()
    ring_shape = CollisionPolygon2D.new()
    ring_points = _build_ring_with_gap(RING_RADIUS, GAP_DEG, 48)
    ring_shape.polygon = ring_points
    ring_body.add_child(ring_shape)
    ring_body.position = Vector2(WIDTH / 2.0, HEIGHT / 2.0)
    add_child(ring_body)


func _physics_process(delta: float) -> void:
    elapsed_s += delta
    ring_body.rotation += ROT_SPEED * delta
    _cleanup_outside()
    if get_tree().get_node_count() < 6 and _ball_count() == 0:
        _spawn_pair()
    queue_redraw()


func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, Vector2(WIDTH, HEIGHT)), Color(0, 0, 0), true)
    draw_circle(Vector2(WIDTH / 2.0, HEIGHT / 2.0), 6.0, Color(1, 1, 1))
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


func _draw_balls() -> void:
    for child in get_children():
        if child is RigidBody2D:
            draw_circle(child.position, RADIUS, Color(0.4, 0.8, 1.0))


func _spawn_pair() -> void:
    if _ball_count() >= MAX_BALLS:
        return
    for i in range(PAIR_SPAWN):
        var ball := RigidBody2D.new()
        ball.gravity_scale = 1.0
        ball.linear_velocity = Vector2.ZERO
        ball.position = Vector2(WIDTH / 2.0 + (i * RADIUS * 2.0), HEIGHT / 2.0)
        var shape := CollisionShape2D.new()
        var circle := CircleShape2D.new()
        circle.radius = RADIUS
        shape.shape = circle
        ball.add_child(shape)
        ball.physics_material_override = PhysicsMaterial.new()
        ball.physics_material_override.bounce = BALL_RESTITUTION
        add_child(ball)


func _cleanup_outside() -> void:
    for child in get_children():
        if child is RigidBody2D:
            if child.position.y > HEIGHT + 200 or child.position.x < -200 or child.position.x > WIDTH + 200:
                child.queue_free()
    if _ball_count() < 2:
        _spawn_pair()


func _ball_count() -> int:
    var count := 0
    for child in get_children():
        if child is RigidBody2D:
            count += 1
    return count


func _build_ring_with_gap(radius: float, gap_deg: float, segments: int) -> PackedVector2Array:
    var points := PackedVector2Array()
    var gap_rad := deg_to_rad(gap_deg)
    var start := gap_rad * 0.5
    var end := TAU - gap_rad * 0.5
    for i in range(segments + 1):
        var t := float(i) / float(segments)
        var angle := start + (end - start) * t
        points.append(Vector2(cos(angle), sin(angle)) * radius)
    return points
