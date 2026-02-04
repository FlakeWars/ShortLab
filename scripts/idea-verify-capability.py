#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from uuid import UUID

from db.models import Idea
from db.session import SessionLocal
from ideas.capability import verify_idea_capability
from sqlalchemy import select


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Idea capability against current DSL")
    parser.add_argument("--idea-id", type=UUID, help="Verify single idea by UUID")
    parser.add_argument("--limit", type=int, default=20, help="Batch size for unverified ideas")
    parser.add_argument("--dsl-version", default="v1")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        reports: list[dict] = []
        if args.idea_id:
            report = verify_idea_capability(
                session,
                idea_id=args.idea_id,
                dsl_version=args.dsl_version,
            )
            reports.append(report)
        else:
            rows = session.execute(
                select(Idea.id)
                .where(Idea.status == "unverified")
                .order_by(Idea.created_at.desc())
                .limit(max(1, args.limit))
            ).all()
            for (idea_id,) in rows:
                reports.append(
                    verify_idea_capability(
                        session,
                        idea_id=idea_id,
                        dsl_version=args.dsl_version,
                    )
                )

        session.commit()
        print(json.dumps({"verified": len(reports), "reports": reports}, ensure_ascii=True))
    finally:
        session.close()


if __name__ == "__main__":
    main()
