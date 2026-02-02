#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from db.models import Job
from db.session import SessionLocal


def main() -> None:
    parser = ArgumentParser(description="Mark stale running jobs as failed")
    parser.add_argument("--older-min", type=int, default=30)
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.older_min)
    session = SessionLocal()
    try:
        stmt = select(Job).where(
            and_(Job.status == "running", Job.updated_at < cutoff)
        )
        jobs = session.execute(stmt).scalars().all()
        for job in jobs:
            job.status = "failed"
            job.error_payload = {"message": f"auto-cleanup: running > {args.older_min} min"}
            job.updated_at = datetime.now(timezone.utc)
            session.add(job)
        session.commit()
        print(f"[cleanup] marked {len(jobs)} job(s) as failed")
    finally:
        session.close()


if __name__ == "__main__":
    main()
