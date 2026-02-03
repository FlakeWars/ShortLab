#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import os

from sqlalchemy import func, select

from db.models import AuditEvent, Idea, IdeaCandidate
from db.session import SessionLocal


def main() -> None:
    parser = ArgumentParser(description="Idea Gate: sample ideas from repository and classify")
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.getenv("IDEA_GATE_COUNT", "3")),
    )
    parser.add_argument("--pick", type=int, default=None, help="Index to pick (1-based)")
    parser.add_argument("--later", default="", help="Comma-separated indices to keep for later")
    parser.add_argument("--reject", default="", help="Comma-separated indices to reject")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        stmt = (
            select(IdeaCandidate)
            .where(IdeaCandidate.status.in_(["new", "later"]))
            .order_by(func.random())
            .limit(max(1, args.count))
        )
        saved = session.execute(stmt).scalars().all()
        if not saved:
            raise SystemExit("No ideas in repository (status new/later)")

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

        if args.pick is None and not args.later and not args.reject:
            print("Use --pick N and classify remaining with --later/--reject.")
            return

        def parse_indices(value: str) -> set[int]:
            if not value:
                return set()
            return {int(item.strip()) for item in value.split(",") if item.strip()}

        picked = {args.pick} if args.pick else set()
        later = parse_indices(args.later)
        rejected = parse_indices(args.reject)
        all_indices = set(range(1, len(saved) + 1))
        selected_indices = picked | later | rejected

        if len(picked) != 1:
            raise SystemExit("Exactly one idea must be picked.")
        if selected_indices != all_indices:
            raise SystemExit("All ideas must be classified (pick/later/reject).")
        if picked & (later | rejected):
            raise SystemExit("Picked idea cannot be in later/reject.")

        now = datetime.now(timezone.utc)
        picked_candidate = saved[args.pick - 1]
        picked_candidate.selected = True
        picked_candidate.selected_at = now
        picked_candidate.status = "picked"
        picked_candidate.decision_at = now

        idea = Idea(
            idea_candidate_id=picked_candidate.id,
            title=picked_candidate.title,
            summary=picked_candidate.summary,
            what_to_expect=picked_candidate.what_to_expect,
            preview=picked_candidate.preview,
            idea_hash=_hash_idea(picked_candidate.title, picked_candidate.summary or ""),
            created_at=now,
        )
        session.add(idea)
        session.flush()

        for idx, candidate in enumerate(saved, start=1):
            if idx in later:
                candidate.status = "later"
                candidate.decision_at = now
                session.add(
                    AuditEvent(
                        event_type="idea_decision",
                        source="cli",
                        occurred_at=now,
                        payload={"idea_candidate_id": candidate.id, "decision": "later"},
                    )
                )
            elif idx in rejected:
                session.add(
                    AuditEvent(
                        event_type="idea_decision",
                        source="cli",
                        occurred_at=now,
                        payload={"idea_candidate_id": candidate.id, "decision": "rejected"},
                    )
                )
                session.delete(candidate)

        session.add(
            AuditEvent(
                event_type="idea_decision",
                source="cli",
                occurred_at=now,
                payload={"idea_id": idea.id, "idea_candidate_id": picked_candidate.id, "decision": "picked"},
            )
        )
        session.commit()

        print(f"[picked] idea_id={idea.id} title={picked_candidate.title}")
    finally:
        session.close()


def _hash_idea(title: str, summary: str) -> str:
    payload = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    main()
