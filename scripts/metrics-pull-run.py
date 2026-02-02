#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone

from db.models import AuditEvent, MetricsPullRun
from db.session import SessionLocal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> None:
    parser = ArgumentParser(description="Create metrics_pull_run row")
    parser.add_argument("--platform", required=True, choices=["youtube", "tiktok"])
    parser.add_argument("--status", default="queued", choices=["queued", "running", "succeeded", "failed"])
    parser.add_argument("--source", default="api", choices=["api", "manual"])
    parser.add_argument("--error", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        now = _utc_now()
        run = MetricsPullRun(
            platform_type=args.platform,
            status=args.status,
            source=args.source,
            started_at=now if args.status in {"running", "succeeded", "failed"} else None,
            finished_at=now if args.status in {"succeeded", "failed"} else None,
            error_payload={"message": args.error} if args.error else None,
            created_at=now,
        )
        session.add(run)
        session.flush()

        audit = AuditEvent(
            event_type="metrics_pull_run",
            source="system",
            actor_user_id=None,
            occurred_at=now,
            payload={
                "platform": args.platform,
                "status": args.status,
                "metrics_pull_run_id": str(run.id),
            },
        )
        session.add(audit)
        session.commit()

        print(f"[metrics-pull] id={run.id} platform={run.platform_type} status={run.status}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
