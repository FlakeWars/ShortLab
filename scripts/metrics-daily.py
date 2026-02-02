#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, timezone
from uuid import UUID

from db.models import AuditEvent, MetricsDaily, PublishRecord, Render
from db.session import SessionLocal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_uuid(value: str) -> UUID:
    return UUID(value)


def main() -> None:
    parser = ArgumentParser(description="Insert metrics_daily row")
    parser.add_argument("--platform", required=True, choices=["youtube", "tiktok"])
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--views", type=int, default=0)
    parser.add_argument("--likes", type=int, default=0)
    parser.add_argument("--comments", type=int, default=0)
    parser.add_argument("--shares", type=int, default=0)
    parser.add_argument("--watch-time-seconds", type=int, default=0)
    parser.add_argument("--avg-view-percentage", type=float, default=None)
    parser.add_argument("--avg-view-duration-seconds", type=int, default=None)
    parser.add_argument("--publish-record-id", default=None)
    parser.add_argument("--render-id", default=None)
    parser.add_argument("--actor", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        publish_record_id = _coerce_uuid(args.publish_record_id) if args.publish_record_id else None
        render_id = _coerce_uuid(args.render_id) if args.render_id else None
        if publish_record_id:
            if session.get(PublishRecord, publish_record_id) is None:
                raise SystemExit("Publish record not found")
        if render_id:
            if session.get(Render, render_id) is None:
                raise SystemExit("Render not found")

        now = _utc_now()
        record = MetricsDaily(
            platform_type=args.platform,
            content_id=args.content_id,
            publish_record_id=publish_record_id,
            render_id=render_id,
            date=date.fromisoformat(args.date),
            views=args.views,
            likes=args.likes,
            comments=args.comments,
            shares=args.shares,
            watch_time_seconds=args.watch_time_seconds,
            avg_view_percentage=args.avg_view_percentage,
            avg_view_duration_seconds=args.avg_view_duration_seconds,
            extra_metrics=None,
            created_at=now,
        )
        session.add(record)
        session.flush()

        actor_id = _coerce_uuid(args.actor) if args.actor else None
        audit = AuditEvent(
            event_type="metrics_daily",
            source="system",
            actor_user_id=actor_id,
            occurred_at=now,
            payload={
                "platform": args.platform,
                "content_id": args.content_id,
                "date": args.date,
                "metrics_daily_id": str(record.id),
            },
        )
        session.add(audit)
        session.commit()

        print(f"[metrics] platform={record.platform_type} content_id={record.content_id} date={record.date}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
