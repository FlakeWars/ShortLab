#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, timezone
import hashlib
from random import Random
import os

from db.models import AuditEvent, Idea, IdeaBatch
from db.session import SessionLocal
from embeddings import EmbeddingConfig, EmbeddingService
from ideas.generator import generate_ideas, save_ideas


def main() -> None:
    parser = ArgumentParser(description="Idea Gate: propose ideas and select one")
    parser.add_argument("--ideas-file", default=".ai/ideas.md")
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "file", "template"],
        help="Idea source provider",
    )
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

    rng = Random(args.seed or int(datetime.now(timezone.utc).strftime("%Y%m%d")))
    drafts = generate_ideas(
        source=args.source,
        ideas_path=args.ideas_file,
        limit=max(1, args.count),
        seed=args.seed or int(rng.random() * 1_000_000),
    )
    if not drafts:
        raise SystemExit("No ideas found")
    rng.shuffle(drafts)
    chosen = drafts[: max(1, min(args.count, len(drafts)))]

    session = SessionLocal()
    try:
        embedder = EmbeddingService(EmbeddingConfig(provider="sklearn-hash"))
        idea_batch = IdeaBatch(
            run_date=date.today(),
            window_id=datetime.now(timezone.utc).strftime("cli-%Y%m%d-%H%M%S"),
            source="manual",
            created_at=datetime.now(timezone.utc),
        )
        session.add(idea_batch)
        session.flush()

        saved = save_ideas(
            session,
            chosen,
            embedder,
            similarity_threshold=args.threshold,
            idea_batch_id=idea_batch.id,
        )

        for idx, idea in enumerate(saved, start=1):
            flag = idea.similarity_status
            sim = getattr(idea, "max_similarity", 0.0) or 0.0
            print(f"[{idx}] {idea.title} (sim={sim:.3f}, {flag})")
            if idea.summary:
                print(f"    Opis: {idea.summary}")
            if getattr(idea, "what_to_expect", ""):
                print(f"    Co zobaczysz: {idea.what_to_expect}")
            if getattr(idea, "preview", ""):
                print(f"    Preview/Reguły: {idea.preview}")

        if args.select is None and not args.auto:
            print("Use --select N or --auto to choose.")
            return

        if args.select is not None:
            if args.select < 1 or args.select > len(saved):
                raise SystemExit("Invalid selection")
            selected = saved[args.select - 1]
            selection_mode = "manual"
        else:
            candidates = [i for i in saved if i.similarity_status != "too_similar"]
            if candidates:
                selected = min(candidates, key=lambda i: getattr(i, "max_similarity", 0.0) or 0.0)
                selection_mode = "auto"
            else:
                selected = min(saved, key=lambda i: getattr(i, "max_similarity", 0.0) or 0.0)
                selection_mode = "auto-all-too-similar"

        selected.selected = True
        selected.selected_at = datetime.now(timezone.utc)
        idea = Idea(
            idea_candidate_id=selected.id,
            title=selected.title,
            summary=selected.summary,
            what_to_expect=selected.what_to_expect,
            preview=selected.preview,
            idea_hash=_hash_idea(selected.title, selected.summary or ""),
            created_at=datetime.now(timezone.utc),
        )
        session.add(idea)
        session.flush()

        audit = AuditEvent(
            event_type="idea_selected",
            source="ui",
            occurred_at=datetime.now(timezone.utc),
            payload={
                "idea_id": idea.id,
                "selection_mode": selection_mode,
                "threshold": args.threshold,
            },
        )
        session.add(audit)
        session.commit()

        print(f"[selected] id={idea.id} title={selected.title}")
    finally:
        session.close()


def _hash_idea(title: str, summary: str) -> str:
    payload = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    main()
