#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from db.models import Animation, AuditEvent, QCChecklistVersion, QCDecision
from db.session import SessionLocal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_uuid(value: str) -> UUID:
    return UUID(value)


def _get_or_create_checklist(session) -> QCChecklistVersion:
    stmt = select(QCChecklistVersion).where(
        QCChecklistVersion.name == "mvp",
        QCChecklistVersion.version == "v1",
    )
    existing = session.execute(stmt).scalars().first()
    if existing:
        return existing
    checklist = QCChecklistVersion(
        name="mvp",
        version="v1",
        is_active=True,
        created_at=_utc_now(),
    )
    session.add(checklist)
    session.flush()
    return checklist


def _apply_status(animation: Animation, result: str) -> None:
    if result == "accepted":
        animation.status = "accepted"
        animation.pipeline_stage = "publish"
        return
    if result == "rejected":
        animation.status = "rejected"
        animation.pipeline_stage = "done"
        return
    if result == "regenerate":
        animation.status = "queued"
        animation.pipeline_stage = "render"
        return
    raise ValueError(f"Unsupported QC result: {result}")


def main() -> None:
    parser = ArgumentParser(description="Create QC decision for an animation")
    parser.add_argument("--animation-id", required=True)
    parser.add_argument(
        "--result",
        required=True,
        choices=["accepted", "rejected", "regenerate"],
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--decided-by", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        animation = session.get(Animation, _coerce_uuid(args.animation_id))
        if animation is None:
            raise SystemExit("Animation not found")

        checklist = _get_or_create_checklist(session)
        decided_by = _coerce_uuid(args.decided_by) if args.decided_by else None
        now = _utc_now()
        decision = QCDecision(
            animation_id=animation.id,
            checklist_version_id=checklist.id,
            result=args.result,
            decision_payload=None,
            notes=args.notes or None,
            decided_by=decided_by,
            decided_at=now,
            created_at=now,
        )
        session.add(decision)

        _apply_status(animation, args.result)
        animation.updated_at = now
        session.add(animation)

        audit = AuditEvent(
            event_type="qc_decision",
            source="ui",
            actor_user_id=decided_by,
            occurred_at=now,
            payload={
                "animation_id": str(animation.id),
                "result": args.result,
                "notes": args.notes,
            },
        )
        session.add(audit)
        session.commit()

        print(f"[qc] animation_id={animation.id} result={args.result}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
