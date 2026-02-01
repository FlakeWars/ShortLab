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
