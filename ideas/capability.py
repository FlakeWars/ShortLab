from __future__ import annotations

import hashlib
import os
import re
from typing import Any
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from db.models import DslGap, Idea, IdeaCandidate, IdeaCandidateGapLink, IdeaGapLink
import yaml

from llm import LLMError, get_mediator
from .prompting import build_idea_context, read_dsl_spec
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

BLOCKING_GAP_STATUSES = {"new", "accepted", "in_progress", "rejected"}
LLM_CAPABILITY_PROMPT_VERSION = "idea-capability-v3"


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


def _active_gap_context(session: Session, *, dsl_version: str) -> str:
    rows = session.execute(
        select(DslGap)
        .where(DslGap.dsl_version == dsl_version)
        .where(DslGap.status.in_(("new", "accepted", "in_progress")))
        .order_by(DslGap.created_at.desc())
        .limit(50)
    ).scalars().all()
    if not rows:
        return ""
    lines = []
    for gap in rows:
        reason = (gap.reason or "").strip()
        lines.append(f"- {gap.feature}: {reason}")
    return "\n".join(lines)


def _llm_capability_check(
    *,
    title: str,
    summary: str | None,
    what_to_expect: str | None,
    preview: str | None,
    dsl_spec: str,
    active_gaps: str,
    language: str,
) -> tuple[dict, dict]:
    language_code = (language or "pl").lower()
    if language_code.startswith("en"):
        response_ok = (
            "{\n"
            '  "feasible": true,\n'
            '  "gaps": [],\n'
            '  "notes": "Brief: idea fully expressible in the current DSL."\n'
            "}\n"
        )
        response_not_ok = (
            "{\n"
            '  "feasible": false,\n'
            '  "gaps": [\n'
            "    {\n"
            '      "feature": "motion_blur_trail",\n'
            '      "reason": "Missing the ability to generate a motion blur trail for fast objects.",\n'
            '      "impact": "Would enable visualizing high-speed motion and its dynamics."\n'
            "    }\n"
            "  ],\n"
            '  "notes": "The idea requires an effect the DSL does not yet support."\n'
            "}\n"
        )
    else:
        response_ok = (
            "{\n"
            '  "feasible": true,\n'
            '  "gaps": [],\n'
            '  "notes": "Krótko: idea w pełni opisywalna DSL."\n'
            "}\n"
        )
        response_not_ok = (
            "{\n"
            '  "feasible": false,\n'
            '  "gaps": [\n'
            "    {\n"
            '      "feature": "motion_blur_trail",\n'
            '      "reason": "Brakuje możliwości generowania smugi ruchu obiektu.",\n'
            '      "impact": "Pozwoliłoby to na wizualizację szybkiego ruchu i jego dynamiki."\n'
            "    }\n"
            "  ],\n"
            '  "notes": "Idea wymaga efektu, którego DSL obecnie nie wspiera."\n'
            "}\n"
        )
    system_prompt = (
        "You verify whether a short animation idea is feasible with the current DSL. "
        "Return JSON only, matching the schema.\n\n"
        "GOAL:\n"
        "We want short, deterministic 2D animations based on simple geometric primitives.\n"
        "The idea should feel visually engaging and somewhat hypnotic, avoid trivial motion,\n"
        "and be feasible for rendering in a structured DSL.\n\n"
        "DSL SPEC (BEGIN):\n"
        "<<<DSL_SPEC_BEGIN>>>\n"
        f"{dsl_spec}\n"
        "<<<DSL_SPEC_END>>>\n\n"
        "EXISTING ACTIVE GAPS (do not repeat unless truly new):\n"
        f"{active_gaps or 'none'}\n\n"
        "EVALUATION FRAME (same as generator):\n"
        "- Use simple geometric primitives.\n"
        "- Motion is deterministic: physics-like forces, parametric paths, or rule-based behaviors.\n"
        "- No external assets, characters, dialog, camera cuts, or photorealism.\n\n"
        "SCHEMA TRAPS (IMPORTANT):\n"
        "- entities.size as object MUST include min and max; no size.value.\n"
        "- spawns do NOT have params at top-level; params live under distribution.\n"
        "- distribution.params must be omitted when not required (e.g., center).\n"
        "- grid requires cols+rows; orbit requires radius (speed optional).\n"
        "- scene.background MUST be one of scene.palette colors.\n\n"
        "ALGORITHM:\n"
        "1) Identify animation elements (visual primitives, motions, forces, timing, interactions).\n"
        "2) Map each element to existing DSL concepts if possible.\n"
        "3) If an element cannot be mapped, define a DSL gap.\n"
        "4) Decide feasibility:\n"
        "   - feasible = true if all essential elements are expressible.\n"
        "   - feasible = false if any essential element is missing OR violates the frame above.\n\n"
        "GAP DEFINITION:\n"
        "Each gap is a missing DSL capability (e.g., visual primitive, motion rule,\n"
        "control/parameter type, or system feature). For each gap provide:\n"
        "- feature: stable snake_case identifier in English\n"
        "- reason: human-readable description of the missing capability\n"
        "- impact: what this feature would enable after implementation\n\n"
        "LANGUAGE:\n"
        "Use the language requested in the USER message for reason/impact/notes.\n"
        "Keep `feature` in English snake_case.\n\n"
        "RESPONSE FORMAT EXAMPLES (BEGIN):\n"
        "<<<RESPONSE_OK>>>\n"
        f"{response_ok}"
        "<<<RESPONSE_NOT_OK>>>\n"
        f"{response_not_ok}"
        "<<<RESPONSE_FORMAT_END>>>\n\n"
        "Return JSON only."
    )
    user_prompt = (
        "IDEA (BEGIN):\n"
        "<<<IDEA_BEGIN>>>\n"
        f"{build_idea_context(title=title, summary=summary, what_to_expect=what_to_expect, preview=preview)}"
        "<<<IDEA_END>>>\n\n"
        f"LANGUAGE: {language.upper()}\n"
    )
    payload, route_meta = get_mediator().generate_json(
        task_type="idea_verify_capability",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_schema={
            "type": "object",
            "properties": {
                "feasible": {"type": "boolean"},
                "gaps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "feature": {"type": "string"},
                            "reason": {"type": "string"},
                            "impact": {"type": "string"},
                        },
                        "required": ["feature", "reason"],
                        "additionalProperties": False,
                    },
                },
                "notes": {"type": "string"},
            },
            "required": ["feasible", "gaps"],
            "additionalProperties": False,
        },
        max_tokens=int(os.getenv("IDEA_DSL_CAPABILITY_MAX_TOKENS", "1200")),
        temperature=float(os.getenv("IDEA_DSL_CAPABILITY_TEMPERATURE", "0.1")),
    )
    return payload, route_meta


def _parse_capability_lenient(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    text = text.replace("```json", "```").replace("```", "")
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    feasible = None
    match = re.search(r"feasible\\s*[:=]\\s*(true|false)", text, re.IGNORECASE)
    if match:
        feasible = match.group(1).lower() == "true"
    gaps: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if not stripped:
            continue
        key_match = re.match(r"^[\"']?([a-zA-Z_]+)[\"']?\\s*:", stripped)
        if not key_match:
            continue
        key = key_match.group(1).lower()
        value = stripped.split(":", 1)[-1].strip().strip(",").strip()
        if key == "feature":
            if current:
                gaps.append(current)
            current = {"feature": value.strip('"\''),}
        elif key == "reason":
            current["reason"] = value.strip('"\'' )
        elif key == "impact":
            current["impact"] = value.strip('"\'' )
    if current:
        gaps.append(current)
    if feasible is None and not gaps:
        return None
    return {"feasible": feasible if feasible is not None else False, "gaps": gaps}


def _ensure_gap(
    session: Session,
    *,
    dsl_version: str,
    signal: GapSignal,
    now: datetime,
) -> tuple[DslGap, bool]:
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
        return gap, True
    return gap, False


def verify_idea_capability(
    session: Session,
    *,
    idea_id: UUID,
    dsl_version: str = "v1",
    policy_version: str = "capability-v1",
    language: str = "pl",
) -> dict:
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise RuntimeError(f"Idea not found: {idea_id}")

    dsl_spec = read_dsl_spec()
    signals: list[GapSignal] = []
    llm_meta: dict[str, str | int | bool] | None = None
    llm_errors: list[str] = []
    use_llm = os.getenv("IDEA_DSL_CAPABILITY_USE_LLM", "1") == "1"
    llm_feasible: bool | None = None
    if use_llm:
        try:
            active_gaps = _active_gap_context(session, dsl_version=dsl_version)
            payload, route_meta = _llm_capability_check(
                title=idea.title,
                summary=idea.summary,
                what_to_expect=idea.what_to_expect,
                preview=idea.preview,
                dsl_spec=dsl_spec,
                active_gaps=active_gaps,
                language=language,
            )
            llm_feasible = bool(payload.get("feasible", True))
            gaps = payload.get("gaps", [])
            for gap in gaps:
                feature = str(gap.get("feature", "")).strip()
                reason = str(gap.get("reason", "")).strip()
                if not feature or not reason:
                    continue
                signals.append(
                    GapSignal(
                        feature=feature,
                        reason=reason,
                        impact=str(gap.get("impact", "")).strip(),
                        keywords=(),
                    )
                )
            llm_meta = {
                "provider": route_meta.get("provider"),
                "model": route_meta.get("model"),
                "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                "llm_feasible": llm_feasible,
                "fallback_used": False,
            }
            if llm_feasible is False and not signals:
                signals.append(
                    GapSignal(
                        feature="dsl_gap_unknown",
                        reason="LLM marked idea infeasible but did not provide explicit gaps.",
                        impact="Manual review required to define missing DSL capability.",
                        keywords=(),
                    )
                )
        except Exception as exc:
            llm_errors.append(str(exc))
            llm_meta = {
                "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                "llm_feasible": llm_feasible,
                "fallback_used": True,
            }
            signals = _extract_signals((idea.title, idea.summary, idea.what_to_expect, idea.preview))
    else:
        signals = _extract_signals((idea.title, idea.summary, idea.what_to_expect, idea.preview))
    now = datetime.now(timezone.utc)
    new_gap_ids: list[UUID] = []
    existing_gap_ids: list[UUID] = []
    blocking_gap_ids: list[UUID] = []
    resolved_gap_ids: list[UUID] = []
    evidence: list[str] = []

    for signal in signals:
        gap, created = _ensure_gap(session, dsl_version=dsl_version, signal=signal, now=now)
        if created:
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
        if gap.status in BLOCKING_GAP_STATUSES:
            blocking_gap_ids.append(gap.id)
        else:
            resolved_gap_ids.append(gap.id)

    fallback_used = bool(llm_meta and llm_meta.get("fallback_used"))
    if fallback_used and not signals:
        feasible = False
    else:
        feasible = len(blocking_gap_ids) == 0
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
        "verifier_meta": llm_meta,
        "verifier_errors": llm_errors,
        "new_gap_ids": [str(gid) for gid in new_gap_ids],
        "existing_gap_ids": [str(gid) for gid in existing_gap_ids],
        "blocking_gap_ids": [str(gid) for gid in blocking_gap_ids],
        "resolved_gap_ids": [str(gid) for gid in resolved_gap_ids],
        "verification_report": {
            "summary": "unverified" if fallback_used and not signals else ("feasible" if feasible else "blocked_by_gaps"),
            "confidence": 0.2 if fallback_used and not signals else (0.95 if feasible else 0.8),
            "evidence": evidence,
        },
    }


def verify_candidate_capability(
    session: Session,
    *,
    idea_candidate_id: UUID,
    dsl_version: str = "v1",
    policy_version: str = "capability-v1",
    language: str = "pl",
) -> dict:
    candidate = session.get(IdeaCandidate, idea_candidate_id)
    if candidate is None:
        raise RuntimeError(f"Idea candidate not found: {idea_candidate_id}")

    dsl_spec = read_dsl_spec()
    signals: list[GapSignal] = []
    llm_meta: dict[str, str | int | bool] | None = None
    llm_errors: list[str] = []
    use_llm = os.getenv("IDEA_DSL_CAPABILITY_USE_LLM", "1") == "1"
    llm_feasible: bool | None = None
    if use_llm:
        try:
            active_gaps = _active_gap_context(session, dsl_version=dsl_version)
            payload, route_meta = _llm_capability_check(
                title=candidate.title,
                summary=candidate.summary,
                what_to_expect=candidate.what_to_expect,
                preview=candidate.preview,
                dsl_spec=dsl_spec,
                active_gaps=active_gaps,
                language=language,
            )
            llm_feasible = bool(payload.get("feasible", True))
            gaps = payload.get("gaps", [])
            for gap in gaps:
                feature = str(gap.get("feature", "")).strip()
                reason = str(gap.get("reason", "")).strip()
                if not feature or not reason:
                    continue
                signals.append(
                    GapSignal(
                        feature=feature,
                        reason=reason,
                        impact=str(gap.get("impact", "")).strip(),
                        keywords=(),
                    )
                )
            llm_meta = {
                "provider": route_meta.get("provider"),
                "model": route_meta.get("model"),
                "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                "llm_feasible": llm_feasible,
                "fallback_used": False,
            }
            if llm_feasible is False and not signals:
                signals.append(
                    GapSignal(
                        feature="dsl_gap_unknown",
                        reason="LLM marked candidate infeasible but did not provide explicit gaps.",
                        impact="Manual review required to define missing DSL capability.",
                        keywords=(),
                    )
                )
        except Exception as exc:
            if isinstance(exc, LLMError) and exc.code == "invalid_json" and exc.raw_content:
                parsed = _parse_capability_lenient(exc.raw_content)
                if parsed:
                    llm_feasible = bool(parsed.get("feasible", True))
                    gaps = parsed.get("gaps", []) if isinstance(parsed.get("gaps"), list) else []
                    for gap in gaps:
                        feature = str(gap.get("feature", "")).strip()
                        reason = str(gap.get("reason", "")).strip()
                        if not feature or not reason:
                            continue
                        signals.append(
                            GapSignal(
                                feature=feature,
                                reason=reason,
                                impact=str(gap.get("impact", "")).strip(),
                                keywords=(),
                            )
                        )
                    llm_meta = {
                        "provider": exc.provider,
                        "model": None,
                        "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                        "llm_feasible": llm_feasible,
                        "fallback_used": False,
                        "parse_mode": "lenient",
                    }
                    if llm_feasible is False and not signals:
                        signals.append(
                            GapSignal(
                                feature="dsl_gap_unknown",
                                reason="LLM output parsed leniently but no explicit gaps returned.",
                                impact="Manual review required to define missing DSL capability.",
                                keywords=(),
                            )
                        )
                else:
                    raw_snippet = exc.raw_content.strip().replace("\n", " ")[:600]
                    llm_errors.append(f"{exc} | raw={raw_snippet}")
                    llm_meta = {
                        "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                        "llm_feasible": llm_feasible,
                        "fallback_used": True,
                    }
                    signals = _extract_signals(
                        (candidate.title, candidate.summary, candidate.what_to_expect, candidate.preview)
                    )
            else:
                llm_errors.append(str(exc))
                llm_meta = {
                    "prompt_version": LLM_CAPABILITY_PROMPT_VERSION,
                    "llm_feasible": llm_feasible,
                    "fallback_used": True,
                }
                signals = _extract_signals(
                    (candidate.title, candidate.summary, candidate.what_to_expect, candidate.preview)
                )
    else:
        signals = _extract_signals((candidate.title, candidate.summary, candidate.what_to_expect, candidate.preview))
    now = datetime.now(timezone.utc)
    new_gap_ids: list[UUID] = []
    existing_gap_ids: list[UUID] = []
    blocking_gap_ids: list[UUID] = []
    resolved_gap_ids: list[UUID] = []
    evidence: list[str] = []

    for signal in signals:
        gap, created = _ensure_gap(session, dsl_version=dsl_version, signal=signal, now=now)
        if created:
            new_gap_ids.append(gap.id)
        else:
            existing_gap_ids.append(gap.id)

        link = session.execute(
            select(IdeaCandidateGapLink).where(
                IdeaCandidateGapLink.idea_candidate_id == candidate.id,
                IdeaCandidateGapLink.dsl_gap_id == gap.id,
            )
        ).scalar_one_or_none()
        if link is None:
            session.add(
                IdeaCandidateGapLink(
                    idea_candidate_id=candidate.id,
                    dsl_gap_id=gap.id,
                    detected_at=now,
                )
            )
        evidence.append(f"{signal.feature}: {signal.reason}")
        if gap.status in BLOCKING_GAP_STATUSES:
            blocking_gap_ids.append(gap.id)
        else:
            resolved_gap_ids.append(gap.id)

    fallback_used = bool(llm_meta and llm_meta.get("fallback_used"))
    if fallback_used and not signals:
        feasible = False
    else:
        feasible = len(blocking_gap_ids) == 0
        candidate.capability_status = "feasible" if feasible else "blocked_by_gaps"
        session.add(candidate)
        if candidate.idea is not None and candidate.idea.status != "compiled":
            candidate.idea.status = "ready_for_gate" if feasible else "blocked_by_gaps"
            session.add(candidate.idea)

    return {
        "idea_candidate_id": str(candidate.id),
        "dsl_version": dsl_version,
        "verification_policy_version": policy_version,
        "feasible": feasible,
        "verifier_meta": llm_meta,
        "verifier_errors": llm_errors,
        "new_gap_ids": [str(gid) for gid in new_gap_ids],
        "existing_gap_ids": [str(gid) for gid in existing_gap_ids],
        "blocking_gap_ids": [str(gid) for gid in blocking_gap_ids],
        "resolved_gap_ids": [str(gid) for gid in resolved_gap_ids],
        "verification_report": {
            "summary": "unverified" if fallback_used and not signals else ("feasible" if feasible else "blocked_by_gaps"),
            "confidence": 0.2 if fallback_used and not signals else (0.95 if feasible else 0.8),
            "evidence": evidence,
        },
    }


def reverify_ideas_for_gap(
    session: Session,
    *,
    dsl_gap_id: UUID,
    dsl_version: str,
    policy_version: str = "capability-v1",
) -> dict:
    gap = session.get(DslGap, dsl_gap_id)
    if gap is None:
        raise RuntimeError(f"DSL gap not found: {dsl_gap_id}")

    rows = session.execute(
        select(IdeaGapLink.idea_id).where(IdeaGapLink.dsl_gap_id == dsl_gap_id)
    ).all()
    reports = []
    for (idea_id,) in rows:
        idea = session.get(Idea, idea_id)
        if idea and idea.status != "compiled":
            idea.status = "unverified"
            session.add(idea)
        reports.append(
            verify_idea_capability(
                session,
                idea_id=idea_id,
                dsl_version=dsl_version,
                policy_version=policy_version,
            )
        )
    feasible_count = sum(1 for report in reports if report["feasible"])
    blocked_count = len(reports) - feasible_count
    return {
        "dsl_gap_id": str(dsl_gap_id),
        "reverified": len(reports),
        "feasible": feasible_count,
        "blocked": blocked_count,
    }


def reverify_candidates_for_gap(
    session: Session,
    *,
    dsl_gap_id: UUID,
    dsl_version: str,
    policy_version: str = "capability-v1",
) -> dict:
    gap = session.get(DslGap, dsl_gap_id)
    if gap is None:
        raise RuntimeError(f"DSL gap not found: {dsl_gap_id}")

    rows = session.execute(
        select(IdeaCandidateGapLink.idea_candidate_id).where(
            IdeaCandidateGapLink.dsl_gap_id == dsl_gap_id
        )
    ).all()
    reports = []
    for (idea_candidate_id,) in rows:
        candidate = session.get(IdeaCandidate, idea_candidate_id)
        if candidate:
            candidate.capability_status = "unverified"
            session.add(candidate)
        reports.append(
            verify_candidate_capability(
                session,
                idea_candidate_id=idea_candidate_id,
                dsl_version=dsl_version,
                policy_version=policy_version,
            )
        )
    feasible_count = sum(1 for report in reports if report["feasible"])
    blocked_count = len(reports) - feasible_count
    return {
        "dsl_gap_id": str(dsl_gap_id),
        "reverified": len(reports),
        "feasible": feasible_count,
        "blocked": blocked_count,
    }
