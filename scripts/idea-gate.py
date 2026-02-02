#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from random import Random
import os

from sqlalchemy import select

from db.models import AuditLog, Idea
from db.session import SessionLocal
from idea_gate.core import (
    content_hash,
    max_similarity,
    parse_ideas,
    text_to_vec,
)


def main() -> None:
    parser = ArgumentParser(description="Idea Gate: propose ideas and select one")
    parser.add_argument("--ideas-file", default=".ai/ideas.md")
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.getenv("IDEA_GATE_COUNT", "3")),
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--select", type=int, default=None)
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("IDEA_GATE_THRESHOLD", "0.85")),
    )
    args = parser.parse_args()

    ideas = parse_ideas(Path(args.ideas_file))
    if not ideas:
        raise SystemExit("No ideas found")

    rng = Random(args.seed or int(datetime.now(timezone.utc).strftime("%Y%m%d")))
    rng.shuffle(ideas)
    chosen = ideas[: max(1, min(args.count, len(ideas)))]

    session = SessionLocal()
    try:
        history = session.execute(select(Idea.embedding).where(Idea.embedding != None)).scalars().all()  # noqa: E711
        history_vecs = [vec for vec in history if isinstance(vec, list)]

        saved: list[Idea] = []
        idea_meta: dict[int, dict] = {}
        for item in chosen:
            vec = text_to_vec(item["title"] + " " + item["summary"])
            similarity = max_similarity(vec, history_vecs)
            idea = Idea(
                title=item["title"],
                summary=item["summary"],
                what_to_expect=item.get("what_to_expect", ""),
                preview=item.get("preview", ""),
                content_hash=content_hash(item["title"], item["summary"]),
                embedding=vec,
                similarity=similarity,
                is_too_similar=similarity >= args.threshold,
            )
            session.add(idea)
            session.commit()
            session.refresh(idea)
            saved.append(idea)
            idea_meta[idea.id] = {
                "what_to_expect": item.get("what_to_expect", ""),
                "preview": item.get("preview", ""),
            }

        for idx, idea in enumerate(saved, start=1):
            flag = "too_similar" if idea.is_too_similar else "ok"
            print(f"[{idx}] {idea.title} (sim={idea.similarity:.3f}, {flag})")
            meta = idea_meta.get(idea.id, {})
            if idea.summary:
                print(f"    Opis: {idea.summary}")
            if meta.get("what_to_expect"):
                print(f"    Co zobaczysz: {meta['what_to_expect']}")
            if meta.get("preview"):
                print(f"    Preview/Reguły: {meta['preview']}")

        if args.select is None and not args.auto:
            print("Use --select N or --auto to choose.")
            return

        if args.select is not None:
            if args.select < 1 or args.select > len(saved):
                raise SystemExit("Invalid selection")
            selected = saved[args.select - 1]
            selection_mode = "manual"
        else:
            candidates = [i for i in saved if not i.is_too_similar]
            if candidates:
                selected = min(candidates, key=lambda i: i.similarity or 0.0)
                selection_mode = "auto"
            else:
                selected = min(saved, key=lambda i: i.similarity or 0.0)
                selection_mode = "auto-all-too-similar"
            selection_mode = "auto"

        audit = AuditLog(
            event_type="idea_selected",
            payload={
                "idea_id": selected.id,
                "selection_mode": selection_mode,
                "threshold": args.threshold,
            },
        )
        session.add(audit)
        session.commit()

        print(f"[selected] id={selected.id} title={selected.title}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
