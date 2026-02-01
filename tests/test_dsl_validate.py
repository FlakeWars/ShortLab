from pathlib import Path

import pytest

from dsl.validate import DSLValidationError, validate_file


FIXTURES_DIR = Path(__file__).parent.parent / ".ai" / "examples"


def test_valid_examples():
    valid_files = [
        FIXTURES_DIR / "dsl-v1-happy.yaml",
        FIXTURES_DIR / "dsl-v1-edge.yaml",
    ]
    for path in valid_files:
        assert validate_file(path) is not None


def test_invalid_missing_entity_reference(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-001"
  title: "Invalid"
  seed: 1
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 10
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "missing"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params: {}
termination:
  time:
    at_s: 10
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_termination_both_time_and_condition(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-002"
  title: "Invalid Termination"
  seed: 1
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 10
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params: {}
termination:
  time:
    at_s: 10
  condition:
    type: "entropy"
    params:
      max_entities: 10
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_rule_missing_required_params(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-003"
  title: "Invalid Rule Params"
  seed: 1
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 10
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move-missing-speed"
      type: "move"
      applies_to: "particle"
      params: {}
termination:
  time:
    at_s: 10
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_rule_unknown_type(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-004"
  title: "Invalid Rule Type"
  seed: 1
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 10
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "unknown"
      type: "teleport"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 10
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_rule_missing_point_fields(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-005"
  title: "Invalid Point"
  seed: 1
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 10
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "orbit-core"
      type: "orbit"
      applies_to: "particle"
      params:
        center:
          x: 100
        speed: 1.0
termination:
  time:
    at_s: 10
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_valid_selector_tag_and_all(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "valid-001"
  title: "Selectors"
  seed: 2
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 2
      distribution:
        type: "center"
  rules:
    - id: "orbit-all"
      type: "orbit"
      applies_to: "all"
      params:
        center: "tag:core"
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "valid.yaml"
    path.write_text(data)
    assert validate_file(path) is not None


def test_invalid_tag_selector_unknown_tag(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-014"
  title: "Invalid Tag Selector"
  seed: 12
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
      tags: ["core"]
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "orbit"
      type: "orbit"
      applies_to: "particle"
      params:
        center: "tag:missing"
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_forces_noise_missing_fields(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-015"
  title: "Invalid Forces"
  seed: 13
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
  forces:
    noise:
      strength: 0.5
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_interactions_when_probability_range(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-016"
  title: "Invalid Interactions"
  seed: 14
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "a"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
    - id: "b"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "a"
      count: 1
      distribution:
        type: "center"
    - entity_id: "b"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "a"
      params:
        speed: 1.0
  interactions:
    pairs:
      - a: "a"
        b: "b"
        rule:
          type: "repel"
          params:
            target: "b"
            strength: 1.0
          when:
            probability: 1.5
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_distribution_grid_missing_params(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-017"
  title: "Invalid Grid"
  seed: 15
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 2
      distribution:
        type: "grid"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_entity_size_minmax(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-018"
  title: "Invalid Size"
  seed: 16
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size:
        min: 10
        max: 2
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_entity_render_opacity(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-019"
  title: "Invalid Render"
  seed: 17
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
      render:
        opacity: 2.0
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_interactions_rule_missing_params(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-020"
  title: "Invalid Interaction Rule"
  seed: 18
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "a"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
    - id: "b"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "a"
      count: 1
      distribution:
        type: "center"
    - entity_id: "b"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "a"
      params:
        speed: 1.0
  interactions:
    pairs:
      - a: "a"
        b: "b"
        rule:
          type: "merge"
          params: {}
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_palette_reference(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-021"
  title: "Invalid Palette"
  seed: 19
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FF00FF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_orbit_speed_negative(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-022"
  title: "Invalid Orbit Speed"
  seed: 20
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "orbit"
        params:
          radius: 10
          speed: -1
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_background_not_in_palette(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-023"
  title: "Invalid Background"
  seed: 21
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#123456"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_palette_format(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-024"
  title: "Invalid Palette Format"
  seed: 22
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "white"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#000000"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_canvas_dims(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-025"
  title: "Invalid Canvas"
  seed: 23
  tags: []
scene:
  canvas:
    width: 0
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_output_resolution_mismatch(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-026"
  title: "Invalid Output Resolution"
  seed: 24
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "720x1280"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_duplicate_ids(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-027"
  title: "Invalid Duplicates"
  seed: 25
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_output_format(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-028"
  title: "Invalid Output Format"
  seed: 26
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "gif"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_output_codec(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-029"
  title: "Invalid Output Codec"
  seed: 27
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "vp9"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_palette_min_size(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-030"
  title: "Invalid Palette Size"
  seed: 28
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#000000"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_emitter_missing_required_fields(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-006"
  title: "Invalid Emitter"
  seed: 3
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  emitters:
    - id: "emitter-1"
      entity_id: "particle"
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_valid_metric_condition_and_fsm(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "valid-002"
  title: "Metrics Contract"
  seed: 4
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
  fsm:
    states: ["a", "b"]
    initial: "a"
    transitions:
      - from: "a"
        to: "b"
        when:
          type: "metric"
          params:
            name: "population"
            op: ">="
            value: 1
termination:
  condition:
    type: "metric"
    params:
      name: "population"
      op: ">="
      value: 1
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "valid.yaml"
    path.write_text(data)
    assert validate_file(path) is not None


def test_invalid_bounds_missing_restitution(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-007"
  title: "Invalid Bounds"
  seed: 5
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
  constraints:
    bounds:
      type: "bounce"
termination:
  time:
    at_s: 5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_condition_missing_fields(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-008"
  title: "Invalid Metric Condition"
  seed: 6
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "population"
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_operator(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-009"
  title: "Invalid Metric Operator"
  seed: 7
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "population"
      op: ">>"
      value: 1
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_name(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-010"
  title: "Invalid Metric Name"
  seed: 8
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "unknown"
      op: ">="
      value: 1
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_value_range(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-011"
  title: "Invalid Metric Range"
  seed: 9
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "coverage"
      op: ">="
      value: 1.5
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_window_negative(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-012"
  title: "Invalid Metric Window"
  seed: 10
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "population"
      op: ">="
      value: 1
      window_s: -1
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)


def test_invalid_metric_sample_gt_window(tmp_path: Path):
    data = """
dsl_version: "1.0"
meta:
  id: "invalid-013"
  title: "Invalid Metric Sample"
  seed: 11
  tags: []
scene:
  canvas:
    width: 1080
    height: 1920
    fps: 30
    duration_s: 5
  palette: ["#000000", "#FFFFFF"]
  background: "#000000"
systems:
  entities:
    - id: "particle"
      shape: "circle"
      size: 8
      color: "#FFFFFF"
  spawns:
    - entity_id: "particle"
      count: 1
      distribution:
        type: "center"
  rules:
    - id: "move"
      type: "move"
      applies_to: "particle"
      params:
        speed: 1.0
termination:
  condition:
    type: "metric"
    params:
      name: "population"
      op: ">="
      value: 1
      window_s: 1
      sample_every_s: 2
output:
  format: "mp4"
  resolution: "1080x1920"
  codec: "h264"
  bitrate: "8M"
"""
    path = tmp_path / "invalid.yaml"
    path.write_text(data)
    with pytest.raises(DSLValidationError):
        validate_file(path)
