#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from renderer.render import render_dsl


EXAMPLES = ROOT / ".ai" / "examples"
GOLDEN_DIR = ROOT / "tests" / "golden"
OUT_DIR = ROOT / "out"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_golden(dsl_name: str, out_name: str) -> None:
    dsl_path = EXAMPLES / dsl_name
    run_dir = OUT_DIR / f"golden-{out_name[:-5]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_video = run_dir / "out.mp4"
    render_dsl(dsl_path, run_dir, out_video)
    meta = run_dir / "metadata.json"
    frames = sorted(run_dir.glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"No frames rendered for {dsl_name}")

    first_idx = 0
    mid_idx = len(frames) // 2
    last_idx = len(frames) - 1
    data = {
        "metadata_sha256": _sha256(meta),
        "frame_index": {
            "first": first_idx,
            "middle": mid_idx,
            "last": last_idx,
        },
        "frame_hashes": {
            "first": _sha256(frames[first_idx]),
            "middle": _sha256(frames[mid_idx]),
            "last": _sha256(frames[last_idx]),
        },
    }
    (GOLDEN_DIR / out_name).write_text(json.dumps(data, indent=2))


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    _write_golden("dsl-v1-happy.yaml", "happy.json")
    _write_golden("dsl-v1-edge.yaml", "edge.json")


if __name__ == "__main__":
    main()
