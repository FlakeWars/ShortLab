from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from db.models import DslGap, Idea, IdeaGapLink
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class GapSignal:
    feature: str
    reason: str
    impact: str
    keywords: tuple[str, ...]


GAP_SIGNALS: tuple[GapSignal, ...] = (
    GapSignal(
        feature="motion_blur_trail",
        reason="Idea requires motion blur/trail post-processing.",
        impact="Current DSL/renderer has no motion blur or trail primitives.",
        keywords=("motion blur", "blur trail", "smuga", "smugi", "rozmycie"),
    ),
    GapSignal(
        feature="volumetric_light",
        reason="Idea requires volumetric or atmospheric light effects.",
        impact="Current DSL has no volumetric lighting controls.",
        keywords=("volumetric", "volumetry", "god rays", "atmospheric light"),
    ),
    GapSignal(
        feature="advanced_audio_sync",
        reason="Idea requires tight sync between timeline events and audio.",
        impact="Current DSL has no direct audio timeline contract.",
        keywords=("audio sync", "sound design", "sfx", "soundtrack"),
    ),
)


def _gap_key(dsl_version: str, feature: str, reason: str) -> str:
    payload = f"{dsl_version}|{feature}|{reason}".lower().encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _extract_signals(text_parts: Iterable[str | None]) -> list[GapSignal]:
    haystack = "\n".join(part.strip().lower() for part in text_parts if part and part.strip())
    matched: list[GapSignal] = []
    for signal in GAP_SIGNALS:
        if any(keyword in haystack for keyword in signal.keywords):
            matched.append(signal)
    return matched


def verify_idea_capability(
    session: Session,
    *,
    idea_id: UUID,
    dsl_version: str = "v1",
    policy_version: str = "capability-v1",
) -> dict:
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise RuntimeError(f"Idea not found: {idea_id}")

    signals = _extract_signals((idea.title, idea.summary, idea.what_to_expect, idea.preview))
    now = datetime.now(timezone.utc)
    new_gap_ids: list[UUID] = []
    existing_gap_ids: list[UUID] = []
    evidence: list[str] = []

    for signal in signals:
        key = _gap_key(dsl_version, signal.feature, signal.reason)
        gap = session.execute(select(DslGap).where(DslGap.gap_key == key)).scalar_one_or_none()
        if gap is None:
            gap = DslGap(
                gap_key=key,
                dsl_version=dsl_version,
                feature=signal.feature,
                reason=signal.reason,
                impact=signal.impact,
                status="new",
                created_at=now,
                updated_at=now,
            )
            session.add(gap)
            session.flush()
            new_gap_ids.append(gap.id)
        else:
            existing_gap_ids.append(gap.id)

        link = session.execute(
            select(IdeaGapLink).where(
                IdeaGapLink.idea_id == idea.id,
                IdeaGapLink.dsl_gap_id == gap.id,
            )
        ).scalar_one_or_none()
        if link is None:
            session.add(
                IdeaGapLink(
                    idea_id=idea.id,
                    dsl_gap_id=gap.id,
                    detected_at=now,
                )
            )
        evidence.append(f"{signal.feature}: {signal.reason}")

    feasible = len(signals) == 0
    if feasible:
        if idea.status not in {"picked", "compiled"}:
            idea.status = "ready_for_gate"
    else:
        if idea.status != "compiled":
            idea.status = "blocked_by_gaps"
    session.add(idea)

    return {
        "idea_id": str(idea.id),
        "dsl_version": dsl_version,
        "verification_policy_version": policy_version,
        "feasible": feasible,
        "new_gap_ids": [str(gid) for gid in new_gap_ids],
        "existing_gap_ids": [str(gid) for gid in existing_gap_ids],
        "verification_report": {
            "summary": "feasible" if feasible else "blocked_by_gaps",
            "confidence": 0.95 if feasible else 0.8,
            "evidence": evidence,
        },
    }
