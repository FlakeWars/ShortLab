extends SceneTree

var script_path := ""
var duration_s := 1.0
var max_nodes := 200
var elapsed_s := 0.0

func _init() -> void:
    var args := OS.get_cmdline_args()
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
        printerr("[runner] missing --script_path")
        OS.set_exit_code(2)
        quit()
        return

    var script := load(script_path)
    if script == null:
        printerr("[runner] failed to load script: " + script_path)
        OS.set_exit_code(3)
        quit()
        return

    var node: Node = script.new()
    if node == null:
        printerr("[runner] failed to instantiate script: " + script_path)
        OS.set_exit_code(4)
        quit()
        return

    get_root().add_child(node)

func _process(delta: float) -> bool:
    elapsed_s += delta
    if get_node_count() > max_nodes:
        printerr("[runner] max_nodes exceeded: " + str(get_node_count()))
        OS.set_exit_code(5)
        quit()
        return true
    if elapsed_s >= duration_s:
        quit()
        return true
    return false
