#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from renderer.render import render_dsl  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsl", required=True, help="Path to DSL YAML/JSON")
    parser.add_argument("--out-dir", required=True, help="Directory for frames/metadata")
    parser.add_argument("--out-video", required=True, help="Output video path")
    args = parser.parse_args()

    render_dsl(args.dsl, args.out_dir, args.out_video)


if __name__ == "__main__":
    main()
