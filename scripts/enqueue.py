#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import os

from pipeline.queue import enqueue_pipeline


def main() -> None:
    parser = ArgumentParser(description="Enqueue minimal pipeline run")
    parser.add_argument(
        "--dsl-template",
        default=".ai/examples/dsl-v1-happy.yaml",
        help="Path to DSL template (YAML/JSON)",
    )
    parser.add_argument(
        "--out-root",
        default="out/pipeline",
        help="Output root directory for artifacts",
    )
    parser.add_argument(
        "--idea-gate",
        action="store_true",
        default=os.getenv("IDEA_GATE_ENABLED", "0") == "1",
        help="Enable Idea Gate selection before DSL generation",
    )
    args = parser.parse_args()

    result = enqueue_pipeline(args.dsl_template, args.out_root, args.idea_gate)
    print("[enqueue] animation_id:", result["animation_id"])
    print("[enqueue] rq_generate_id:", result["rq_generate_id"])
    print("[enqueue] rq_render_id:", result["rq_render_id"])


if __name__ == "__main__":
    main()
