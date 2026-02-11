from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from uuid import UUID

from db.models import Idea
from db.session import SessionLocal
from ideas.godot_compiler import compile_idea_to_gdscript


def parse_args():
    parser = ArgumentParser(description="Compile one feasible idea to GDScript")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--out-root", default="out/manual-gdscript")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--validate-seconds", type=float, default=2.0)
    parser.add_argument("--max-nodes", type=int, default=200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    idea_id = UUID(args.idea_id)
    session = SessionLocal()
    try:
        idea = session.get(Idea, idea_id)
        if idea is None:
            raise RuntimeError(f"Idea not found: {idea_id}")
        out_dir = Path(args.out_root) / f"idea-{idea.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / "script.gd"
        result = compile_idea_to_gdscript(
            idea=idea,
            target_path=target_path,
            max_attempts=max(1, args.max_attempts),
            max_repairs=max(0, args.max_repairs),
            validate=bool(args.validate),
            validate_seconds=args.validate_seconds,
            max_nodes=args.max_nodes,
        )
        print(
            f"[idea-compile-gdscript] idea_id={idea.id} script_path={target_path} "
            f"script_hash={result.script_hash} attempts={result.compiler_meta.get('attempt_count')}"
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
