#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from db.models import Job
from db.session import SessionLocal


def main() -> None:
    parser = ArgumentParser(description="Purge failed jobs older than N minutes")
    parser.add_argument("--older-min", type=int, default=60)
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.older_min)
    session = SessionLocal()
    try:
        stmt = select(Job.id).where(Job.status == "failed", Job.updated_at < cutoff)
        ids = [row[0] for row in session.execute(stmt).all()]
        if not ids:
            print("[purge] removed 0 job(s)")
            return
        session.execute(delete(Job).where(Job.id.in_(ids)))
        session.commit()
        print(f"[purge] removed {len(ids)} job(s)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
