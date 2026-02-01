#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dsl.validate import DSLValidationError  # noqa: E402
from renderer.render import render_dsl  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsl", required=True, help="Path to DSL YAML/JSON")
    parser.add_argument("--out-dir", required=True, help="Directory for frames/metadata")
    parser.add_argument("--out-video", required=True, help="Output video path")
    args = parser.parse_args()

    try:
        dsl_path = Path(args.dsl)
        if not dsl_path.exists():
            raise SystemExit(f"[render-cli] DSL file not found: {dsl_path}")
        if dsl_path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            raise SystemExit("[render-cli] DSL file must be .yaml, .yml, or .json")

        out_dir = Path(args.out_dir)
        out_video = Path(args.out_video)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_video.parent.mkdir(parents=True, exist_ok=True)

        render_dsl(str(dsl_path), str(out_dir), str(out_video))
    except DSLValidationError as exc:
        raise SystemExit(f"[render-cli] DSL validation error: {exc}") from exc


if __name__ == "__main__":
    main()
