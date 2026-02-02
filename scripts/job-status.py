#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser

from sqlalchemy import desc, func, select

from db.models import Job
from db.session import SessionLocal


def main() -> None:
    parser = ArgumentParser(description="Show recent job statuses")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--failed", action="store_true", help="Show failed jobs with error payload")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        if args.summary:
            stmt = select(Job.status, func.count()).group_by(Job.status)
            rows = session.execute(stmt).all()
            for status, count in rows:
                print(f"[summary] {status}: {count}")
            return
        stmt = select(Job)
        if args.failed:
            stmt = stmt.where(Job.status == "failed")
        stmt = stmt.order_by(desc(Job.created_at)).limit(args.limit)
        jobs = session.execute(stmt).scalars().all()
        for job in jobs:
            payload = job.payload or {}
            error_payload = job.error_payload or {}
            print(
                f"[job] id={job.id} kind={job.job_type} status={job.status} rq_id={payload.get('rq_id')}"
            )
            if args.failed and error_payload:
                print(f"[job] error={error_payload}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
