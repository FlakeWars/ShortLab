#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from uuid import UUID

from db.models import DslGap
from db.session import SessionLocal
from ideas.capability import reverify_candidates_for_gap, reverify_ideas_for_gap


def main() -> None:
    parser = argparse.ArgumentParser(description="Update DSL gap status and reverify linked ideas")
    parser.add_argument("--gap-id", type=UUID, required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=["new", "accepted", "in_progress", "implemented", "rejected"],
    )
    parser.add_argument("--implemented-in", dest="implemented_in", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        gap = session.get(DslGap, args.gap_id)
        if gap is None:
            raise SystemExit(f"dsl_gap not found: {args.gap_id}")

        gap.status = args.status
        gap.updated_at = datetime.now(timezone.utc)
        if args.status == "implemented":
            if not args.implemented_in:
                raise SystemExit("--implemented-in is required when status=implemented")
            gap.implemented_in_version = args.implemented_in
        session.add(gap)

        dsl_version = args.implemented_in or gap.dsl_version
        reverify_candidates = reverify_candidates_for_gap(session, dsl_gap_id=gap.id, dsl_version=dsl_version)
        reverify_ideas = reverify_ideas_for_gap(session, dsl_gap_id=gap.id, dsl_version=dsl_version)
        session.commit()
        print(
            json.dumps(
                {
                    "gap_id": str(gap.id),
                    "status": gap.status,
                    "reverify_candidates": reverify_candidates,
                    "reverify_ideas": reverify_ideas,
                },
                ensure_ascii=True,
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
