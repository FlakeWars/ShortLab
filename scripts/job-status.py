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
    args = parser.parse_args()

    session = SessionLocal()
    try:
        if args.summary:
            stmt = select(Job.status, func.count()).group_by(Job.status)
            rows = session.execute(stmt).all()
            for status, count in rows:
                print(f"[summary] {status}: {count}")
            return
        stmt = select(Job).order_by(desc(Job.id)).limit(args.limit)
        jobs = session.execute(stmt).scalars().all()
        for job in jobs:
            print(
                f"[job] id={job.id} kind={job.kind} status={job.status} rq_id={job.rq_id}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
