#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser

from pipeline.queue import enqueue_render


def main() -> None:
    parser = ArgumentParser(description="Manually rerun render for an animation")
    parser.add_argument("--animation-id", type=int, required=True)
    parser.add_argument(
        "--out-root",
        default="out/pipeline",
        help="Output root directory for artifacts",
    )
    args = parser.parse_args()

    result = enqueue_render(args.animation_id, args.out_root)
    print("[rerun] animation_id:", result["animation_id"])
    print("[rerun] rq_render_id:", result["rq_render_id"])


if __name__ == "__main__":
    main()
