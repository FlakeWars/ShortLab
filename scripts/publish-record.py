#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from db.models import AuditEvent, PublishRecord, Render
from db.session import SessionLocal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_uuid(value: str) -> UUID:
    return UUID(value)


def main() -> None:
    parser = ArgumentParser(description="Create publish record for a render")
    parser.add_argument("--render-id", required=True)
    parser.add_argument("--platform", required=True, choices=["youtube", "tiktok"])
    parser.add_argument(
        "--status",
        default="queued",
        choices=["queued", "uploading", "published", "failed", "manual_confirmed"],
    )
    parser.add_argument("--content-id", default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--scheduled-for", default=None)
    parser.add_argument("--published-at", default=None)
    parser.add_argument("--error", default=None)
    parser.add_argument("--actor", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        render = session.get(Render, _coerce_uuid(args.render_id))
        if render is None:
            raise SystemExit("Render not found")

        now = _utc_now()
        scheduled_for = None
        published_at = None
        if args.scheduled_for:
            scheduled_for = datetime.fromisoformat(args.scheduled_for)
        if args.published_at:
            published_at = datetime.fromisoformat(args.published_at)

        record = PublishRecord(
            render_id=render.id,
            platform_type=args.platform,
            status=args.status,
            content_id=args.content_id,
            url=args.url,
            scheduled_for=scheduled_for,
            published_at=published_at,
            error_payload={"message": args.error} if args.error else None,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()

        actor_id = _coerce_uuid(args.actor) if args.actor else None
        audit = AuditEvent(
            event_type="publish_record",
            source="ui",
            actor_user_id=actor_id,
            occurred_at=now,
            payload={
                "render_id": str(render.id),
                "publish_record_id": str(record.id),
                "platform": args.platform,
                "status": args.status,
            },
        )
        session.add(audit)
        session.commit()

        print(f"[publish] id={record.id} platform={record.platform_type} status={record.status}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
