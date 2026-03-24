extends SceneTree

var script_path := ""
var duration_s := 1.0
var max_nodes := 200
var elapsed_s := 0.0
var scene_node: Node2D

var estimate_enabled := false
var estimate_threshold := 0.85
var estimate_hold_s := 2.0
var estimate_sample_s := 0.5
var estimate_hold_start_s := -1.0
var estimate_effect_time_s := -1.0
var estimate_reached := false
var estimate_progress := -1.0
var estimate_last_sample_s := -1.0

func _init() -> void:
    var args := OS.get_cmdline_args()
    var sep_index := args.find("--")
    if sep_index >= 0:
        args = args.slice(sep_index + 1, args.size())
    var i := 0
    while i < args.size():
        match args[i]:
            "--script_path":
                if i + 1 < args.size():
                    script_path = args[i + 1]
                i += 2
            "--seconds":
                if i + 1 < args.size():
                    duration_s = float(args[i + 1])
                i += 2
            "--max_nodes":
                if i + 1 < args.size():
                    max_nodes = int(args[i + 1])
                i += 2
            _:
                i += 1

    if script_path == "":
        script_path = OS.get_environment("GODOT_SCRIPT_PATH")
    var env_seconds := OS.get_environment("GODOT_SECONDS")
    if env_seconds != "":
        duration_s = float(env_seconds)
    var env_max_nodes := OS.get_environment("GODOT_MAX_NODES")
    if env_max_nodes != "":
        max_nodes = int(env_max_nodes)
    var env_estimate := OS.get_environment("GODOT_ESTIMATE_ENABLED")
    estimate_enabled = env_estimate == "1"
    var env_threshold := OS.get_environment("GODOT_ESTIMATE_THRESHOLD")
    if env_threshold != "":
        estimate_threshold = clamp(float(env_threshold), 0.0, 1.0)
    var env_hold := OS.get_environment("GODOT_ESTIMATE_HOLD_SECONDS")
    if env_hold != "":
        estimate_hold_s = max(0.1, float(env_hold))
    var env_sample := OS.get_environment("GODOT_ESTIMATE_SAMPLE_SECONDS")
    if env_sample != "":
        estimate_sample_s = max(0.1, float(env_sample))

    if script_path == "":
        printerr("[runner] missing --script_path")
        quit(2)
        return
    if not script_path.begins_with("res://"):
        script_path = ProjectSettings.localize_path(script_path)
    if not script_path.begins_with("res://"):
        printerr("[runner] script_path must be res:// or within project: " + script_path)
        quit(2)
        return

    var script := load(script_path)
    if script == null:
        printerr("[runner] failed to load script: " + script_path)
        quit(3)
        return

    scene_node = Node2D.new()
    scene_node.set_script(script)
    get_root().add_child(scene_node)

func _extract_effect_progress(node: Node) -> float:
    if node == null:
        return -1.0
    if node.has_method("effect_progress"):
        var value: Variant = node.call("effect_progress")
        if typeof(value) in [TYPE_FLOAT, TYPE_INT]:
            return clamp(float(value), 0.0, 1.0)
    if node.has_method("get_effect_progress"):
        var getter_value: Variant = node.call("get_effect_progress")
        if typeof(getter_value) in [TYPE_FLOAT, TYPE_INT]:
            return clamp(float(getter_value), 0.0, 1.0)
    if node.has_meta("effect_progress"):
        var meta_value: Variant = node.get_meta("effect_progress")
        if typeof(meta_value) in [TYPE_FLOAT, TYPE_INT]:
            return clamp(float(meta_value), 0.0, 1.0)
    return -1.0

func _estimate_tick() -> void:
    if not estimate_enabled:
        return
    if elapsed_s - estimate_last_sample_s < estimate_sample_s:
        return
    estimate_last_sample_s = elapsed_s
    estimate_progress = _extract_effect_progress(scene_node)
    if estimate_progress < 0.0:
        return
    if estimate_progress >= estimate_threshold:
        if estimate_hold_start_s < 0.0:
            estimate_hold_start_s = elapsed_s
        if not estimate_reached and (elapsed_s - estimate_hold_start_s) >= estimate_hold_s:
            estimate_reached = true
            estimate_effect_time_s = estimate_hold_start_s
    else:
        estimate_hold_start_s = -1.0

func _print_estimate_summary() -> void:
    if not estimate_enabled:
        return
    var reached := "1" if estimate_reached else "0"
    var effect_time := str(estimate_effect_time_s if estimate_effect_time_s >= 0.0 else -1.0)
    var progress := str(estimate_progress)
    var support := "1" if estimate_progress >= 0.0 else "0"
    print(
        "[runner:estimate] summary reached=%s effect_time_s=%s threshold=%s hold_s=%s progress=%s support=%s"
        % [reached, effect_time, str(estimate_threshold), str(estimate_hold_s), progress, support]
    )

func _process(delta: float) -> bool:
    elapsed_s += delta
    _estimate_tick()
    if get_node_count() > max_nodes:
        printerr("[runner] max_nodes exceeded: " + str(get_node_count()))
        quit(5)
        return true
    if elapsed_s >= duration_s:
        _print_estimate_summary()
        quit()
        return true
    return false
