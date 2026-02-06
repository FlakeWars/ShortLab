#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from uuid import UUID

from db.models import IdeaCandidate
from db.session import SessionLocal
from ideas.capability import verify_candidate_capability
from sqlalchemy import select


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify IdeaCandidate capability against current DSL")
    parser.add_argument("--idea-candidate-id", type=UUID, help="Verify single idea candidate by UUID")
    parser.add_argument("--limit", type=int, default=20, help="Batch size for unverified idea candidates")
    parser.add_argument("--dsl-version", default="v1")
    parser.add_argument(
        "--language",
        default="pl",
        choices=["pl", "en"],
        help="Language for gap reason/impact",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        reports: list[dict] = []
        if args.idea_candidate_id:
            report = verify_candidate_capability(
                session,
                idea_candidate_id=args.idea_candidate_id,
                dsl_version=args.dsl_version,
                language=args.language,
            )
            reports.append(report)
        else:
            rows = session.execute(
                select(IdeaCandidate.id)
                .where(IdeaCandidate.capability_status == "unverified")
                .order_by(IdeaCandidate.created_at.desc())
                .limit(max(1, args.limit))
            ).all()
            for (candidate_id,) in rows:
                reports.append(
                    verify_candidate_capability(
                        session,
                        idea_candidate_id=candidate_id,
                        dsl_version=args.dsl_version,
                        language=args.language,
                    )
                )

        session.commit()
        print(json.dumps({"verified": len(reports), "reports": reports}, ensure_ascii=True))
    finally:
        session.close()


if __name__ == "__main__":
    main()
