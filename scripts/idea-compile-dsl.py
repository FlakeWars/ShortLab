from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from uuid import UUID, uuid4

from db.models import Idea
from db.session import SessionLocal
from ideas.compiler import compile_idea_to_dsl


def parse_args():
    parser = ArgumentParser(description="Compile one feasible idea to DSL")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--dsl-template", default=".ai/examples/dsl-v1-happy.yaml")
    parser.add_argument("--out-root", default="out/manual-compile")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-repairs", type=int, default=2)
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
        target_path = out_dir / "dsl.yaml"
        result = compile_idea_to_dsl(
            idea=idea,
            template_path=Path(args.dsl_template),
            target_path=target_path,
            animation_code=uuid4().hex,
            max_attempts=max(1, args.max_attempts),
            max_repairs=max(0, args.max_repairs),
        )
        idea.status = "compiled"
        session.add(idea)
        session.commit()
        print(
            f"[idea-compile-dsl] idea_id={idea.id} dsl_path={target_path} "
            f"dsl_hash={result.dsl_hash} fallback={result.compiler_meta.get('fallback_used')}"
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
