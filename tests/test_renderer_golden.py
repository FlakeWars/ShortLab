from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from renderer.render import render_dsl


ROOT = Path(__file__).parent.parent
EXAMPLES = ROOT / ".ai" / "examples"
GOLDEN_DIR = Path(__file__).parent / "golden"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _render_and_hash(dsl_path: Path, out_dir: Path) -> dict[str, str]:
    out_video = out_dir / "out.mp4"
    render_dsl(dsl_path, out_dir, out_video)
    meta = out_dir / "metadata.json"
    return {
        "video_sha256": _sha256(out_video),
        "metadata_sha256": _sha256(meta),
    }


@pytest.mark.parametrize(
    "dsl_name, golden_name",
    [
        ("dsl-v1-happy.yaml", "happy.json"),
        ("dsl-v1-edge.yaml", "edge.json"),
    ],
)
def test_renderer_golden(dsl_name: str, golden_name: str, tmp_path: Path):
    dsl_path = EXAMPLES / dsl_name
    golden_path = GOLDEN_DIR / golden_name
    if not golden_path.exists():
        pytest.fail(f"Golden file missing: {golden_path}")

    hashes = _render_and_hash(dsl_path, tmp_path)
    expected = json.loads(golden_path.read_text())
    assert hashes == expected
