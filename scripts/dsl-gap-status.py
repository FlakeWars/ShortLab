#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from uuid import UUID

from db.models import DslGap
from db.session import SessionLocal
from ideas.capability import reverify_ideas_for_gap


def main() -> None:
    parser = argparse.ArgumentParser(description="Update DSL gap status and reverify linked ideas")
    parser.add_argument("--gap-id", type=UUID, required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=["new", "accepted", "in_progress", "implemented", "rejected"],
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        gap = session.get(DslGap, args.gap_id)
        if gap is None:
            raise SystemExit(f"dsl_gap not found: {args.gap_id}")

        gap.status = args.status
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)

        reverify = reverify_ideas_for_gap(session, dsl_gap_id=gap.id)
        session.commit()
        print(json.dumps({"gap_id": str(gap.id), "status": gap.status, "reverify": reverify}, ensure_ascii=True))
    finally:
        session.close()


if __name__ == "__main__":
    main()
