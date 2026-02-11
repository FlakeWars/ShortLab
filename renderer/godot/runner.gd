extends SceneTree

var script_path := ""
var duration_s := 1.0
var max_nodes := 200
var elapsed_s := 0.0

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

    var node := Node2D.new()
    node.set_script(script)
    get_root().add_child(node)

func _process(delta: float) -> bool:
    elapsed_s += delta
    if get_node_count() > max_nodes:
        printerr("[runner] max_nodes exceeded: " + str(get_node_count()))
        quit(5)
        return true
    if elapsed_s >= duration_s:
        quit()
        return true
    return false
