from ideas.godot_compiler import _extract_gdscript_from_raw_llm_content


def test_extract_gdscript_from_truncated_json_string() -> None:
    raw = '{"code":"extends Node2D\\n\\nfunc _ready() -> void:\\n    queue_redraw()'
    script = _extract_gdscript_from_raw_llm_content(raw)
    assert script.startswith("extends Node2D")
    assert "func _ready()" in script


def test_extract_gdscript_from_fenced_block() -> None:
    raw = "```gdscript\nextends Node2D\n\nfunc _ready() -> void:\n    pass\n```"
    script = _extract_gdscript_from_raw_llm_content(raw)
    assert script.startswith("extends Node2D")
    assert "func _ready()" in script
