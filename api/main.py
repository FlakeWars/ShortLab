from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import re
import tempfile
import time
import unicodedata
from os import getenv
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional, Literal
from uuid import UUID
from uuid import uuid4
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy import and_, delete, desc, func, select, text

from embeddings import EmbeddingConfig, EmbeddingService
from db.models import (
    Animation,
    AuditEvent,
    Artifact,
    DslGap,
    DslVersion,
    Idea,
    IdeaCandidate,
    IdeaCandidateGapLink,
    IdeaEmbedding,
    IdeaGapLink,
    IdeaBatch,
    MetricsDaily,
    PublishRecord,
    QCChecklistVersion,
    QCDecision,
    Render,
    Job,
)
from db.session import SessionLocal
from ideas.capability import (
    reverify_candidates_for_gap,
    reverify_ideas_for_gap,
    verify_candidate_capability,
    verify_idea_capability,
)
from ideas.compiler import compile_idea_to_dsl
from ideas.godot_compiler import compile_idea_to_gdscript
from ideas.generator import IdeaDraft, _is_valid, generate_ideas, save_ideas
from ideas.parser import parse_ideas_text
from llm import get_mediator
from llm.mediator import _load_route, _load_routes

app = FastAPI(title="ShortLab API", version="0.1.0")

_SYSTEM_STATUS_CACHE_PAYLOAD: dict | None = None
_SYSTEM_STATUS_CACHE_EXPIRES_AT: float = 0.0

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _paginate(limit: int, offset: int) -> tuple[int, int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return limit, offset


def _encode(obj) -> dict:
    return jsonable_encoder(obj)


def _hash_idea(title: str, summary: str) -> str:
    payload = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_operator(x_operator_token: str | None = Header(default=None)) -> None:
    expected = getenv("OPERATOR_TOKEN", "")
    if not expected:
        if getenv("ALLOW_OPS_WITHOUT_TOKEN", "0") == "1":
            return
        raise HTTPException(status_code=503, detail="operator_token_missing")
    if x_operator_token != expected:
        raise HTTPException(status_code=401, detail="operator_token_required")


def _artifact_base_dir() -> Path:
    base_dir = getenv("ARTIFACTS_BASE_DIR", "out")
    return Path(base_dir).expanduser().resolve()


def _manual_godot_root() -> Path:
    return Path(getenv("MANUAL_GODOT_OUT_ROOT", "out/manual-godot")).expanduser().resolve()


def _planner_settings_file() -> Path:
    return (Path(getenv("PLANNER_SETTINGS_FILE", "out/planner/settings.json")).expanduser().resolve())


def _publish_readiness_summary_file() -> Path:
    return (
        Path(getenv("PUBLISH_READINESS_SUMMARY_FILE", "out/reports/publish-readiness-summary-latest.json"))
        .expanduser()
        .resolve()
    )


def _repo_root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _local_script_path(script_name: str) -> Path:
    return (_repo_root_dir() / "scripts" / script_name).resolve()


def _run_local_script(script_name: str, args: list[str], timeout_s: int = 120) -> dict:
    script_path = _local_script_path(script_name)
    if not script_path.exists():
        return {
            "ok": False,
            "script": script_name,
            "error": "script_not_found",
            "script_path": str(script_path),
        }
    cmd = [sys.executable, str(script_path), *args]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(_repo_root_dir()),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "script": script_name,
            "error": "timeout",
            "timeout_s": timeout_s,
            "stdout": (exc.stdout or "").strip()[-8000:],
            "stderr": (exc.stderr or "").strip()[-8000:],
            "cmd": cmd,
        }
    return {
        "ok": completed.returncode == 0,
        "script": script_name,
        "cmd": cmd,
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-8000:],
        "stderr": (completed.stderr or "").strip()[-8000:],
    }


def _read_publish_readiness_summary() -> tuple[dict | None, str | None]:
    path = _publish_readiness_summary_file()
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "invalid"
    if not isinstance(payload, dict):
        return None, "invalid"
    payload["source_file"] = str(path)
    return payload, None


def _planner_settings_defaults() -> dict:
    return {
        "timezone": getenv("PLANNER_TIMEZONE", "UTC"),
        "daily_publish_hour": int(getenv("PLANNER_DAILY_HOUR", "18")),
        "daily_publish_minute": int(getenv("PLANNER_DAILY_MINUTE", "0")),
        "publish_window_minutes": int(getenv("PLANNER_WINDOW_MINUTES", "120")),
        "target_per_day": int(getenv("PLANNER_TARGET_PER_DAY", "1")),
    }


def _system_status_cache_ttl_s() -> int:
    raw = getenv("SYSTEM_STATUS_CACHE_TTL_S", "5") or "5"
    try:
        value = int(raw)
    except ValueError:
        value = 5
    return max(0, min(value, 60))


def _load_planner_settings() -> dict:
    path = _planner_settings_file()
    payload = _planner_settings_defaults()
    if not path.exists():
        return payload
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return payload
    if isinstance(raw, dict):
        payload.update({k: raw[k] for k in payload.keys() if k in raw})
    return payload


def _save_planner_settings(payload: dict) -> dict:
    path = _planner_settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _planner_status_snapshot(session) -> dict:
    cfg = _load_planner_settings()
    tz_name = str(cfg.get("timezone") or "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
        tz_name = "UTC"
        cfg["timezone"] = "UTC"

    now_utc = _utc_now()
    now_local = now_utc.astimezone(tz)
    hour = int(cfg.get("daily_publish_hour", 18))
    minute = int(cfg.get("daily_publish_minute", 0))
    window_minutes = int(cfg.get("publish_window_minutes", 120))
    target_per_day = int(cfg.get("target_per_day", 1))
    window_start_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    window_end_local = window_start_local + timedelta(minutes=window_minutes)
    in_window = window_start_local <= now_local <= window_end_local
    local_day = now_local.date()

    recent_publish = session.execute(
        select(PublishRecord).where(PublishRecord.created_at >= now_utc - timedelta(days=3))
    ).scalars().all()
    published_today = 0
    for row in recent_publish:
        if row.status not in {"published", "manual_confirmed"}:
            continue
        source_ts = row.published_at or row.created_at
        if source_ts is None:
            continue
        if source_ts.astimezone(tz).date() == local_day:
            published_today += 1

    pending_jobs_today = session.execute(
        select(func.count())
        .select_from(Job)
        .where(
            and_(
                Job.status.in_(["queued", "running"]),
                Job.job_type.in_(["generate_dsl", "render"]),
                Job.created_at >= now_utc - timedelta(days=1),
            )
        )
    ).scalar_one()

    should_enqueue = in_window and published_today < target_per_day and int(pending_jobs_today or 0) == 0
    reason = "ready"
    if not in_window:
        reason = "outside_window"
    elif published_today >= target_per_day:
        reason = "target_reached"
    elif int(pending_jobs_today or 0) > 0:
        reason = "pending_jobs"

    return {
        "timezone": tz_name,
        "now_utc": now_utc,
        "now_local": now_local.isoformat(),
        "local_day": str(local_day),
        "window_start_local": window_start_local.isoformat(),
        "window_end_local": window_end_local.isoformat(),
        "window_minutes": window_minutes,
        "target_per_day": target_per_day,
        "published_today": published_today,
        "pending_jobs_today": int(pending_jobs_today or 0),
        "in_window": in_window,
        "should_enqueue": should_enqueue,
        "reason": reason,
        "settings": cfg,
    }


def _manual_godot_history_file() -> Path:
    return _manual_godot_root() / "_history" / "manual-runs.jsonl"


def _manual_godot_history_max_lines() -> int:
    raw = getenv("MANUAL_GODOT_HISTORY_MAX_LINES", "200")
    try:
        value = int(raw)
    except ValueError:
        value = 200
    return max(10, min(value, 5000))


def _manual_godot_history_record(
    *,
    step: Literal["compile", "validate", "estimate", "intent_check", "preview", "render"],
    ok: bool,
    actor_user_id: UUID | None = None,
    idea_id: UUID | None = None,
    payload: dict | None = None,
    error: str | None = None,
) -> dict:
    payload = payload or {}
    return {
        "id": str(uuid4()),
        "recorded_at": _utc_now().isoformat(),
        "step": step,
        "ok": bool(ok),
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "idea_id": str(idea_id) if idea_id else None,
        "script_path": payload.get("script_path"),
        "out_path": payload.get("out_path"),
        "out_exists": payload.get("out_exists"),
        "log_file": payload.get("log_file"),
        "exit_code": payload.get("exit_code"),
        "script_hash": payload.get("script_hash"),
        "estimate": payload.get("estimate"),
        "recommended_sim_duration_s": payload.get("recommended_sim_duration_s"),
        "recommended_speed_factor": payload.get("recommended_speed_factor"),
        "target_duration_s": payload.get("target_duration_s"),
        "target_runtime_s": payload.get("target_runtime_s"),
        "intent_reached": payload.get("intent_reached"),
        "intent_reached_at_s": payload.get("intent_reached_at_s"),
        "intent_progress": payload.get("intent_progress"),
        "intent_status": payload.get("intent_status"),
        "blocking_reason": payload.get("blocking_reason"),
        "confidence": payload.get("confidence"),
        "method": payload.get("method"),
        "error": error,
    }


def _append_manual_godot_history(record: dict) -> None:
    path = _manual_godot_history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True))
        handle.write("\n")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        max_lines = _manual_godot_history_max_lines()
        if len(lines) > max_lines:
            path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except Exception:
        # Best-effort rotation; history write should not fail the operator action.
        return


def _read_manual_godot_history(*, limit: int = 20, step: str | None = None, script_path: str | None = None) -> list[dict]:
    path = _manual_godot_history_file()
    if not path.exists():
        return []
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if step and str(row.get("step")) != step:
            continue
        if script_path and str(row.get("script_path")) != script_path:
            continue
        rows.append(row)
    rows.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
    return rows[: max(1, min(limit, 100))]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_qc_checklist(session) -> QCChecklistVersion:
    existing = session.execute(
        select(QCChecklistVersion).where(
            QCChecklistVersion.name == "mvp",
            QCChecklistVersion.version == "v1",
        )
    ).scalars().first()
    if existing is not None:
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


def _apply_qc_result(animation: Animation, result: str) -> None:
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
    raise ValueError(f"unsupported_qc_result:{result}")


def _apply_publish_status(animation: Animation, status: str) -> None:
    if status in {"queued", "uploading", "failed"}:
        animation.pipeline_stage = "publish"
        if animation.status not in {"accepted", "published"}:
            animation.status = "accepted"
        return
    if status in {"published", "manual_confirmed"}:
        animation.status = "published"
        animation.pipeline_stage = "metrics"
        return
    raise ValueError(f"unsupported_publish_status:{status}")


def _validate_publish_record_request(request: "PublishRecordCreateRequest") -> None:
    status = request.status
    content_id = (request.content_id or "").strip()
    url = (request.url or "").strip()
    error_text = (request.error or "").strip()
    if status in {"published", "manual_confirmed"} and not (content_id or url):
        raise HTTPException(
            status_code=400,
            detail="publish_record_requires_content_id_or_url_for_published_status",
        )
    if status == "failed" and not error_text:
        raise HTTPException(status_code=400, detail="publish_record_requires_error_for_failed_status")
    if url:
        normalized = url.lower()
        has_youtube = "youtube.com/" in normalized or "youtu.be/" in normalized
        has_tiktok = "tiktok.com/" in normalized
        if request.platform == "youtube" and has_tiktok:
            raise HTTPException(status_code=400, detail="publish_record_url_platform_mismatch")
        if request.platform == "tiktok" and has_youtube:
            raise HTTPException(status_code=400, detail="publish_record_url_platform_mismatch")


def _validate_qc_decision_request(request: "QcDecisionCreateRequest") -> None:
    if request.result != "accepted":
        return
    payload = request.decision_payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="qc_payload_must_be_object")
    required_true = {
        "idea_intent_ok",
        "intro_readability_ok",
        "audio_quality_ok",
    }
    missing = [key for key in sorted(required_true) if payload.get(key) is not True]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"qc_accept_requires_true_flags:{','.join(missing)}",
        )


def _audit_event(session, *, event_type: str, payload: dict, actor_user_id: UUID | None = None) -> None:
    session.add(
        AuditEvent(
            event_type=event_type,
            source="ui",
            actor_user_id=actor_user_id,
            occurred_at=_utc_now(),
            payload=payload,
        )
    )


def _latest_godot_log_file(before: set[Path] | None = None) -> Path | None:
    log_dir = (Path(__file__).resolve().parents[1] / "out" / "godot" / "logs").resolve()
    if not log_dir.exists():
        return None
    files = sorted(log_dir.glob("godot-run-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    if before is None:
        return files[0]
    for file in files:
        if file not in before:
            return file
    return files[0]


def _run_godot_manual_step(
    *,
    mode: Literal["validate", "preview", "render", "estimate"],
    script_path: Path,
    seconds: float,
    fps: int,
    max_nodes: int,
    out_path: Path | None = None,
    scale: float | None = None,
    estimate_threshold: float | None = None,
    estimate_hold_seconds: float | None = None,
    estimate_sample_seconds: float | None = None,
) -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "godot-run.py"),
        "--mode",
        mode,
        "--script",
        str(script_path.resolve()),
        "--seconds",
        str(seconds),
        "--fps",
        str(fps),
        "--max-nodes",
        str(max_nodes),
    ]
    if out_path is not None:
        cmd.extend(["--out", str(out_path.resolve())])
    if scale is not None:
        cmd.extend(["--scale", str(scale)])
    if mode == "estimate":
        cmd.extend(
            [
                "--estimate-threshold",
                str(estimate_threshold if estimate_threshold is not None else 0.85),
                "--estimate-hold-seconds",
                str(estimate_hold_seconds if estimate_hold_seconds is not None else 2.0),
                "--estimate-sample-seconds",
                str(estimate_sample_seconds if estimate_sample_seconds is not None else 0.5),
            ]
        )

    before_logs = set()
    latest_before = _latest_godot_log_file()
    if latest_before is not None:
        log_dir = latest_before.parent
        if log_dir.exists():
            before_logs = set(log_dir.glob("godot-run-*.log"))
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    latest_log = _latest_godot_log_file(before_logs or None)
    payload = {
        "mode": mode,
        "script_path": str(script_path.resolve()),
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-8000:],
        "stderr": (completed.stderr or "").strip()[-8000:],
        "log_file": str(latest_log) if latest_log else None,
    }
    if out_path is not None:
        payload["out_path"] = str(out_path.resolve())
        payload["out_exists"] = out_path.exists()
    if mode == "estimate":
        combined = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        summary = re.search(
            r"\[godot-run-estimate\]\s+reached=([-0-9.]+)\s+effect_time_s=([-0-9.]+)\s+threshold=([-0-9.]+)\s+hold_s=([-0-9.]+)\s+progress=([-0-9.]+)\s+support=([-0-9.]+)",
            combined,
        )
        if summary:
            payload["estimate"] = {
                "reached": int(float(summary.group(1))) == 1,
                "effect_time_s": float(summary.group(2)),
                "threshold": float(summary.group(3)),
                "hold_s": float(summary.group(4)),
                "progress": float(summary.group(5)),
                "support": int(float(summary.group(6))) == 1,
            }
    payload["ok"] = completed.returncode == 0
    return payload


def _worker_state() -> dict:
    try:
        from rq import Worker
        from pipeline.queue import get_queue, get_redis

        redis = get_redis()
        redis.ping()
        queue = get_queue()
        workers = Worker.all(connection=redis)
        return {
            "redis_ok": True,
            "online": len(workers) > 0,
            "worker_count": len(workers),
            "queue_depth": queue.count,
        }
    except Exception:
        return {
            "redis_ok": False,
            "online": False,
            "worker_count": 0,
            "queue_depth": None,
        }


def _service_status(name: str, ok: bool, details: str | None = None) -> dict:
    return {
        "service": name,
        "status": "ok" if ok else "down",
        "details": details,
    }


def _repo_counts(session, model, status_col=None) -> dict:
    total = session.execute(select(func.count()).select_from(model)).scalar_one()
    payload = {"total": int(total), "by_status": {}}
    if status_col is not None:
        rows = session.execute(select(status_col, func.count()).group_by(status_col)).all()
        payload["by_status"] = {str(status or "unknown"): int(count) for status, count in rows}
    return payload


def _activate_dsl_version(session, *, version: str, notes: str | None = None) -> DslVersion:
    row = session.execute(select(DslVersion).where(DslVersion.version == version)).scalar_one_or_none()
    if row is None:
        row = DslVersion(version=version, schema_json={}, is_active=True, notes=notes)
        session.add(row)
    else:
        row.is_active = True
        if notes:
            row.notes = notes
    session.execute(
        sa.update(DslVersion).where(DslVersion.version != version).values(is_active=False)
    )
    session.flush()
    return row


def _dev_manual_flow_enabled() -> bool:
    return getenv("DEV_MANUAL_FLOW", "0").lower() in {"1", "true", "yes"}


def _animation_row(animation: Animation, render: Render | None, qc: QCDecision | None) -> dict:
    payload = {
        "id": animation.id,
        "animation_code": animation.animation_code,
        "status": animation.status,
        "pipeline_stage": animation.pipeline_stage,
        "idea_id": animation.idea_id,
        "created_at": animation.created_at,
        "updated_at": animation.updated_at,
    }
    if render is not None:
        payload["render"] = {
            "id": render.id,
            "status": render.status,
            "seed": render.seed,
            "dsl_version_id": render.dsl_version_id,
            "design_system_version_id": render.design_system_version_id,
            "renderer_version": render.renderer_version,
            "duration_ms": render.duration_ms,
            "width": render.width,
            "height": render.height,
            "fps": float(render.fps) if render.fps is not None else None,
            "created_at": render.created_at,
            "started_at": render.started_at,
            "finished_at": render.finished_at,
        }
    if qc is not None:
        payload["qc"] = {
            "id": qc.id,
            "result": qc.result,
            "checklist_version_id": qc.checklist_version_id,
            "decided_at": qc.decided_at,
        }
    return jsonable_encoder(payload)


class EnqueueRequest(BaseModel):
    dsl_template: str = Field(default=".ai/examples/dsl-v1-happy.yaml")
    out_root: str = Field(default="out/pipeline")
    idea_gate: bool = Field(default=False)
    idea_id: UUID | None = Field(default=None)


class IdeaDecisionItem(BaseModel):
    idea_candidate_id: UUID
    decision: Literal["picked", "later", "rejected"]


class IdeaDecisionRequest(BaseModel):
    decisions: List[IdeaDecisionItem]


class IdeaCapabilityVerifyRequest(BaseModel):
    idea_id: UUID
    dsl_version: str = Field(default="v1")
    language: Literal["pl", "en"] = Field(default="pl")


class IdeaCapabilityVerifyBatchRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=200)
    dsl_version: str = Field(default="v1")
    language: Literal["pl", "en"] = Field(default="pl")


class IdeaCandidateCapabilityVerifyRequest(BaseModel):
    idea_candidate_id: UUID
    dsl_version: str = Field(default="v1")
    language: Literal["pl", "en"] = Field(default="pl")


class IdeaCandidateCapabilityVerifyBatchRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=200)
    dsl_version: str = Field(default="v1")
    language: Literal["pl", "en"] = Field(default="pl")


class IdeaCandidateCapabilityOverrideRequest(BaseModel):
    status: Literal["unverified", "feasible", "blocked_by_gaps"]
    reason: str | None = None


class DslGapStatusRequest(BaseModel):
    status: Literal["new", "accepted", "in_progress", "implemented", "rejected"]
    implemented_in_dsl_version: Optional[str] = None
    notes: Optional[str] = None


class RerunRequest(BaseModel):
    animation_id: UUID
    out_root: str = Field(default="out/pipeline")


class CleanupRequest(BaseModel):
    older_min: int = Field(default=30, ge=1, le=1440)


class IdeaCompileRequest(BaseModel):
    dsl_template: str = Field(default=".ai/examples/dsl-v1-happy.yaml")
    out_root: str = Field(default="out/manual-compile")
    max_attempts: int = Field(default=3, ge=1, le=10)
    max_repairs: int = Field(default=2, ge=0, le=10)


class IdeaCandidateGenerateRequest(BaseModel):
    mode: Literal["llm", "text", "file"]
    limit: int | None = Field(default=None, ge=1, le=50)
    prompt: str | None = Field(default=None)
    language: Literal["pl", "en"] = Field(default="pl")
    text: str | None = Field(default=None)
    title: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    what_to_expect: str | None = Field(default=None)
    preview: str | None = Field(default=None)
    file_name: str | None = Field(default=None)
    file_content: str | None = Field(default=None)


class QcDecisionCreateRequest(BaseModel):
    animation_id: UUID
    result: Literal["accepted", "rejected", "regenerate"]
    notes: str | None = Field(default=None)
    decided_by: UUID | None = Field(default=None)
    decision_payload: dict | None = Field(default=None)


class PublishRecordCreateRequest(BaseModel):
    render_id: UUID
    platform: Literal["youtube", "tiktok"]
    status: Literal["queued", "uploading", "published", "failed", "manual_confirmed"] = Field(
        default="manual_confirmed"
    )
    content_id: str | None = Field(default=None)
    url: str | None = Field(default=None)
    scheduled_for: datetime | None = Field(default=None)
    published_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None)
    actor: UUID | None = Field(default=None)


class MetricsDailyManualUpsertRequest(BaseModel):
    platform_type: Literal["youtube", "tiktok"]
    content_id: str = Field(min_length=1, max_length=256)
    date: date
    publish_record_id: UUID | None = Field(default=None)
    render_id: UUID | None = Field(default=None)
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    watch_time_seconds: int = Field(default=0, ge=0)
    avg_view_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    avg_view_duration_seconds: int | None = Field(default=None, ge=0)
    audio_profile: Literal["balanced", "speech", "music", "sfx_heavy"] | None = Field(default=None)
    extra_metrics: dict | None = Field(default=None)
    actor: UUID | None = Field(default=None)


class GodotManualCompileRequest(BaseModel):
    idea_id: UUID
    out_root: str = Field(default="out/manual-godot")
    max_attempts: int = Field(default=3, ge=1, le=10)
    max_repairs: int = Field(default=2, ge=0, le=10)
    validate_after_compile: bool = Field(default=False, alias="validate")
    validate_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    max_nodes: int = Field(default=200, ge=10, le=5000)
    actor: UUID | None = Field(default=None)


class GodotManualRunRequest(BaseModel):
    script_path: str
    seconds: float = Field(default=2.0, ge=0.1, le=300.0)
    fps: int = Field(default=12, ge=1, le=120)
    max_nodes: int = Field(default=200, ge=10, le=5000)
    out_path: str | None = Field(default=None)
    scale: float | None = Field(default=None, ge=0.1, le=2.0)
    actor: UUID | None = Field(default=None)


class GodotEstimateDurationRequest(BaseModel):
    script_path: str
    target_duration_s: float = Field(default=30.0, ge=1.0, le=300.0)
    scout_seconds: float = Field(default=60.0, ge=2.0, le=600.0)
    fps: int = Field(default=12, ge=1, le=120)
    max_nodes: int = Field(default=200, ge=10, le=5000)
    threshold: float = Field(default=0.85, ge=0.1, le=1.0)
    hold_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    sample_seconds: float = Field(default=0.5, ge=0.1, le=10.0)
    tail_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
    actor: UUID | None = Field(default=None)


class GodotIntentCheckRequest(BaseModel):
    script_path: str
    runtime_override_s: float | None = Field(default=None, ge=1.0, le=300.0)
    scout_seconds: float = Field(default=60.0, ge=2.0, le=600.0)
    fps: int = Field(default=12, ge=1, le=120)
    max_nodes: int = Field(default=200, ge=10, le=5000)
    threshold: float = Field(default=0.85, ge=0.1, le=1.0)
    hold_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    sample_seconds: float = Field(default=0.5, ge=0.1, le=10.0)
    tail_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
    actor: UUID | None = Field(default=None)


class IntroOverlayRequest(BaseModel):
    input_path: str
    out_path: str | None = Field(default=None)
    intro_text: str | None = Field(default=None)
    idea_id: UUID | None = Field(default=None)
    language: Literal["pl", "en"] | None = Field(default=None)
    duration_s: float = Field(default=1.5, ge=0.5, le=4.0)
    max_chars: int = Field(default=90, ge=20, le=200)
    font_size: int = Field(default=52, ge=16, le=128)
    actor: UUID | None = Field(default=None)


class AudioMixRequest(BaseModel):
    input_path: str
    out_path: str | None = Field(default=None)
    music_path: str | None = Field(default=None)
    sfx_path: str | None = Field(default=None)
    keep_source_audio: bool = Field(default=False)
    music_gain_db: float = Field(default=-18.0, ge=-60.0, le=12.0)
    sfx_gain_db: float = Field(default=-6.0, ge=-60.0, le=12.0)
    normalize_loudness: bool = Field(default=True)
    target_lufs: float = Field(default=-16.0, ge=-30.0, le=-5.0)
    true_peak_db: float = Field(default=-1.0, ge=-9.0, le=0.0)
    audio_profile: str | None = Field(default=None)
    actor: UUID | None = Field(default=None)


class LaterCleanupRequest(BaseModel):
    max_age_days: int | None = Field(default=None, ge=1, le=3650)
    dry_run: bool = Field(default=False)
    actor: UUID | None = Field(default=None)


class PlannerSettingsUpdateRequest(BaseModel):
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    daily_publish_hour: int = Field(default=18, ge=0, le=23)
    daily_publish_minute: int = Field(default=0, ge=0, le=59)
    publish_window_minutes: int = Field(default=120, ge=15, le=1440)
    target_per_day: int = Field(default=1, ge=1, le=20)


class PlannerTickRequest(BaseModel):
    force: bool = Field(default=False)
    dsl_template: str = Field(default=".ai/examples/dsl-v1-happy.yaml")
    out_root: str = Field(default="out/pipeline")
    idea_gate: bool = Field(default=False)


class PublishReadinessRefreshRequest(BaseModel):
    run_mcp_audit: bool = Field(default=True)
    run_compliance_check: bool = Field(default=True)
    run_oauth_smoke: bool = Field(default=True)
    oauth_online: bool = Field(default=False)
    oauth_require: Literal["none", "passed_if_configured", "passed_all"] = Field(
        default="passed_if_configured"
    )
    mcp_audit_fail_on_risk_level: Literal["none", "high", "medium"] = Field(default="none")
    compliance_require: Literal["none", "strict"] = Field(default="none")
    summary_max_allowed_risk: Literal["low", "medium", "high"] = Field(default="medium")
    summary_require_pass: bool = Field(default=False)
    timeout_s: int = Field(default=120, ge=10, le=1200)
    actor: UUID | None = Field(default=None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/system/status")
def system_status() -> dict:
    global _SYSTEM_STATUS_CACHE_PAYLOAD, _SYSTEM_STATUS_CACHE_EXPIRES_AT
    started = time.perf_counter()
    now_ts = time.time()
    cache_ttl_s = _system_status_cache_ttl_s()
    if cache_ttl_s > 0 and _SYSTEM_STATUS_CACHE_PAYLOAD is not None and now_ts < _SYSTEM_STATUS_CACHE_EXPIRES_AT:
        payload = dict(_SYSTEM_STATUS_CACHE_PAYLOAD)
        payload["cache"] = {"hit": True, "ttl_s": cache_ttl_s}
        return payload

    updated_at = datetime.now(timezone.utc)
    partial_failures: list[str] = []
    worker = _worker_state()
    services = [
        _service_status("api", True),
        _service_status("redis", bool(worker.get("redis_ok")), None if worker.get("redis_ok") else "ping_failed"),
        _service_status("worker", bool(worker.get("online")), f"count={worker.get('worker_count', 0)}"),
    ]

    artifacts_dir = _artifact_base_dir()
    storage_ok = artifacts_dir.exists()
    services.append(
        _service_status(
            "storage",
            storage_ok,
            str(artifacts_dir) if storage_ok else f"missing:{artifacts_dir}",
        )
    )
    if not storage_ok:
        partial_failures.append("storage_unavailable")

    repo_counts: dict[str, dict] = {
        "ideas": {"total": None, "by_status": {}},
        "idea_candidates": {"total": None, "by_status": {}},
        "dsl_gaps": {"total": None, "by_status": {}},
        "animations": {"total": None, "by_status": {}},
        "renders": {"total": None, "by_status": {}},
        "artifacts": {"total": None, "by_status": {}},
        "jobs": {"total": None, "by_status": {}},
        "sfx": {"total": None, "by_status": {}, "placeholder": True},
        "music": {"total": None, "by_status": {}, "placeholder": True},
    }

    session = SessionLocal()
    try:
        session.execute(text("select 1"))
        services.append(_service_status("postgres", True))
        repo_counts["ideas"] = _repo_counts(session, Idea, Idea.status)
        candidate_total = session.execute(select(func.count()).select_from(IdeaCandidate)).scalar_one()
        candidate_by_status = session.execute(
            select(IdeaCandidate.status, func.count()).group_by(IdeaCandidate.status)
        ).all()
        candidate_by_capability = session.execute(
            select(IdeaCandidate.capability_status, func.count()).group_by(IdeaCandidate.capability_status)
        ).all()
        repo_counts["idea_candidates"] = {
            "total": int(candidate_total),
            "by_status": {str(status or "unknown"): int(count) for status, count in candidate_by_status},
            "by_capability": {str(status or "unknown"): int(count) for status, count in candidate_by_capability},
        }
        repo_counts["dsl_gaps"] = _repo_counts(session, DslGap, DslGap.status)
        repo_counts["animations"] = _repo_counts(session, Animation, Animation.status)
        repo_counts["renders"] = _repo_counts(session, Render, Render.status)
        repo_counts["jobs"] = _repo_counts(session, Job, Job.status)
        artifacts_total = session.execute(select(func.count()).select_from(Artifact)).scalar_one()
        artifacts_by_type = session.execute(
            select(Artifact.artifact_type, func.count()).group_by(Artifact.artifact_type)
        ).all()
        repo_counts["artifacts"] = {
            "total": int(artifacts_total),
            "by_status": {str(kind or "unknown"): int(count) for kind, count in artifacts_by_type},
        }
        active_version = session.execute(
            select(DslVersion).where(DslVersion.is_active.is_(True)).limit(1)
        ).scalar_one_or_none()
        if active_version is None:
            active_version = _activate_dsl_version(
                session, version=getenv("DSL_CURRENT_VERSION", "v1")
            )
        current_dsl_version = active_version.version
    except Exception as exc:
        services.append(_service_status("postgres", False, "query_failed"))
        partial_failures.append(f"postgres_unavailable:{type(exc).__name__}")
    finally:
        session.close()

    payload = {
        "service_status": services,
        "repo_counts": repo_counts,
        "worker": worker,
        "dsl_version_current": current_dsl_version if "current_dsl_version" in locals() else None,
        "updated_at": updated_at,
        "partial_failures": partial_failures,
        "response_time_ms": int((time.perf_counter() - started) * 1000),
        "cache": {"hit": False, "ttl_s": cache_ttl_s},
    }
    if cache_ttl_s > 0:
        _SYSTEM_STATUS_CACHE_PAYLOAD = payload
        _SYSTEM_STATUS_CACHE_EXPIRES_AT = now_ts + cache_ttl_s
    return payload


@app.get("/settings")
def get_settings() -> dict:
    def flag(name: str, default: str = "") -> str:
        return getenv(name, default)

    return {
        "database_url": flag("DATABASE_URL", ""),
        "redis_url": flag("REDIS_URL", ""),
        "rq_job_timeout": flag("RQ_JOB_TIMEOUT", "120"),
        "rq_render_timeout": flag("RQ_RENDER_TIMEOUT", "600"),
        "ffmpeg_timeout_s": flag("FFMPEG_TIMEOUT_S", "120"),
        "idea_gate_enabled": flag("IDEA_GATE_ENABLED", "0"),
        "idea_gate_count": flag("IDEA_GATE_COUNT", "3"),
        "idea_gate_threshold": flag("IDEA_GATE_THRESHOLD", "0.85"),
        "idea_gate_auto": flag("IDEA_GATE_AUTO", "0"),
        "dev_manual_flow": flag("DEV_MANUAL_FLOW", "0"),
        "operator_single_video_mode": flag("OPERATOR_SINGLE_VIDEO_MODE", "1"),
        "operator_target_runtime_s": flag("OPERATOR_TARGET_RUNTIME_S", "60"),
        "operator_intro_language": flag("OPERATOR_INTRO_LANGUAGE", "en"),
        "operator_later_max_age_days": flag("OPERATOR_LATER_MAX_AGE_DAYS", "30"),
        "system_status_cache_ttl_s": flag("SYSTEM_STATUS_CACHE_TTL_S", "5"),
        "operator_guard": flag("OPERATOR_TOKEN", "") != "",
        "artifacts_base_dir": flag("ARTIFACTS_BASE_DIR", "out"),
        "openai_model": flag("OPENAI_MODEL", ""),
        "openai_base_url": flag("OPENAI_BASE_URL", ""),
        "openai_temperature": flag("OPENAI_TEMPERATURE", "0.7"),
        "openai_max_output_tokens": flag("OPENAI_MAX_OUTPUT_TOKENS", "800"),
        "llm_token_budgets": flag("LLM_TOKEN_BUDGETS", ""),
    }


@app.get("/planner/settings")
def get_planner_settings() -> dict:
    payload = _load_planner_settings()
    tz_name = str(payload.get("timezone") or "UTC")
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        payload["timezone"] = "UTC"
    return payload


@app.post("/ops/planner/settings")
def set_planner_settings(
    request: PlannerSettingsUpdateRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    try:
        ZoneInfo(request.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=400, detail="planner_timezone_invalid")
    return jsonable_encoder(_save_planner_settings(request.model_dump()))


@app.get("/planner/status")
def get_planner_status() -> dict:
    session = SessionLocal()
    try:
        snapshot = _planner_status_snapshot(session)
        return jsonable_encoder(snapshot)
    finally:
        session.close()


@app.post("/ops/planner/tick")
def planner_tick(
    request: PlannerTickRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    from pipeline.queue import enqueue_pipeline

    session = SessionLocal()
    try:
        snapshot = _planner_status_snapshot(session)
        will_enqueue = bool(snapshot["should_enqueue"]) or request.force
        result = None
        if will_enqueue:
            result = enqueue_pipeline(
                request.dsl_template,
                request.out_root,
                request.idea_gate,
                None,
            )
            _audit_event(
                session,
                event_type="planner_tick_enqueue",
                payload={
                    "forced": request.force,
                    "reason": snapshot["reason"],
                    "window_day": snapshot["local_day"],
                    "animation_id": str(result.get("animation_id")) if isinstance(result, dict) else None,
                },
            )
            session.commit()
            snapshot = _planner_status_snapshot(session)
        else:
            _audit_event(
                session,
                event_type="planner_tick_skip",
                payload={
                    "forced": request.force,
                    "reason": snapshot["reason"],
                    "window_day": snapshot["local_day"],
                },
            )
            session.commit()

        return jsonable_encoder(
            {
                "triggered": will_enqueue,
                "forced": request.force,
                "reason": snapshot["reason"] if not will_enqueue else "enqueued",
                "planner_status": snapshot,
                "enqueue_result": result,
            }
        )
    finally:
        session.close()


@app.post("/ops/publish/readiness-refresh")
def ops_publish_readiness_refresh(
    request: PublishReadinessRefreshRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    script_results: list[dict] = []
    if request.run_mcp_audit:
        script_results.append(
            _run_local_script(
                "mcp-publish-audit.py",
                ["--fail-on-risk-level", request.mcp_audit_fail_on_risk_level],
                timeout_s=request.timeout_s,
            )
        )
    if request.run_compliance_check:
        script_results.append(
            _run_local_script(
                "mcp-compliance-check.py",
                ["--require", request.compliance_require],
                timeout_s=request.timeout_s,
            )
        )
    if request.run_oauth_smoke:
        oauth_args = ["--require", request.oauth_require]
        if request.oauth_online:
            oauth_args.append("--online")
        script_results.append(
            _run_local_script(
                "publish-oauth-smoke.py",
                oauth_args,
                timeout_s=request.timeout_s,
            )
        )

    summary_args = [
        "--max-allowed-risk",
        request.summary_max_allowed_risk,
    ]
    if request.summary_require_pass:
        summary_args.append("--require-pass")
    summary_result = _run_local_script(
        "publish-readiness-summary.py",
        summary_args,
        timeout_s=request.timeout_s,
    )
    script_results.append(summary_result)

    scripts_ok = all(bool(item.get("ok")) for item in script_results)
    summary_payload, summary_error = _read_publish_readiness_summary()
    overall_pass = bool(summary_payload.get("overall_pass")) if summary_payload else False
    payload = {
        "ok": scripts_ok and summary_error is None,
        "scripts_ok": scripts_ok,
        "summary_available": summary_payload is not None and summary_error is None,
        "summary_error": summary_error,
        "overall_pass": overall_pass,
        "script_results": script_results,
        "readiness_summary": summary_payload,
        "updated_at": _utc_now(),
    }

    session = SessionLocal()
    try:
        _audit_event(
            session,
            event_type="publish_readiness_refresh",
            actor_user_id=request.actor,
            payload={
                "ok": payload["ok"],
                "scripts_ok": scripts_ok,
                "overall_pass": overall_pass,
                "summary_error": summary_error,
                "script_results": [
                    {
                        "script": str(item.get("script", "")),
                        "ok": bool(item.get("ok")),
                        "exit_code": item.get("exit_code"),
                        "error": item.get("error"),
                    }
                    for item in script_results
                ],
            },
        )
        session.commit()
    finally:
        session.close()

    return jsonable_encoder(payload)


@app.get("/debug/llm-routes")
def debug_llm_routes(_guard: None = Depends(_require_operator)) -> dict:
    tasks = [
        "idea_generate",
        "idea_verify_capability",
        "idea_compile_dsl",
        "dsl_repair",
        "gdscript_generate",
        "gdscript_repair",
    ]
    routes: dict[str, dict[str, str | bool]] = {}
    for task in tasks:
        try:
            candidates = []
            for route in _load_routes(task):
                candidates.append(
                    {
                        "provider": route.provider,
                        "model": route.model,
                        "base_url": route.base_url,
                        "api_key_header": route.api_key_header,
                        "api_key_present": bool(route.api_key),
                    }
                )
            routes[task] = {
                "primary": candidates[0] if candidates else {},
                "candidates": candidates,
            }
        except Exception as exc:
            routes[task] = {"error": str(exc)}
    return {"routes": routes}


@app.get("/audit-events")
def list_audit_events(
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    actor_user_id: Optional[UUID] = None,
    occurred_after: Optional[datetime] = None,
    occurred_before: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(AuditEvent)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if source:
            stmt = stmt.where(AuditEvent.source == source)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if occurred_after:
            stmt = stmt.where(AuditEvent.occurred_at >= occurred_after)
        if occurred_before:
            stmt = stmt.where(AuditEvent.occurred_at <= occurred_before)
        stmt = stmt.order_by(desc(AuditEvent.occurred_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/metrics-daily")
def list_metrics_daily(
    platform_type: Optional[str] = None,
    content_id: Optional[str] = None,
    render_id: Optional[UUID] = None,
    publish_record_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(MetricsDaily)
        if platform_type:
            stmt = stmt.where(MetricsDaily.platform_type == platform_type)
        if content_id:
            stmt = stmt.where(MetricsDaily.content_id == content_id)
        if render_id:
            stmt = stmt.where(MetricsDaily.render_id == render_id)
        if publish_record_id:
            stmt = stmt.where(MetricsDaily.publish_record_id == publish_record_id)
        if date_from:
            stmt = stmt.where(MetricsDaily.date >= date_from)
        if date_to:
            stmt = stmt.where(MetricsDaily.date <= date_to)
        stmt = stmt.order_by(desc(MetricsDaily.date)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/insights/summary")
def get_insights_summary(
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        now = _utc_now()
        recent_from = now.date() - timedelta(days=13)
        metrics_rows = session.execute(
            select(MetricsDaily).where(MetricsDaily.date >= recent_from)
        ).scalars().all()
        publish_rows = session.execute(
            select(PublishRecord).where(
                PublishRecord.created_at >= now - timedelta(days=14)
            )
        ).scalars().all()
        intro_audit_rows = session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "intro_overlay_generate",
                AuditEvent.occurred_at >= now - timedelta(days=14),
            )
        ).scalars().all()
        return jsonable_encoder(
            _build_insights_summary(
                metrics_rows=list(metrics_rows),
                publish_rows=list(publish_rows),
                intro_audit_rows=list(intro_audit_rows),
                now=now,
            )
        )
    finally:
        session.close()


@app.post("/ops/metrics-daily")
def upsert_metrics_daily_manual(
    request: MetricsDailyManualUpsertRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        publish_record: PublishRecord | None = None
        if request.publish_record_id:
            publish_record = session.get(PublishRecord, request.publish_record_id)
            if publish_record is None:
                raise HTTPException(status_code=404, detail="publish_record_not_found")
        if request.render_id:
            render = session.get(Render, request.render_id)
            if render is None:
                raise HTTPException(status_code=404, detail="render_not_found")

        content_id = request.content_id.strip()
        stmt = select(MetricsDaily).where(
            MetricsDaily.platform_type == request.platform_type,
            MetricsDaily.content_id == content_id,
            MetricsDaily.date == request.date,
        )
        record = session.execute(stmt).scalars().first()
        created = record is None
        if record is None:
            record = MetricsDaily(
                platform_type=request.platform_type,
                content_id=content_id,
                date=request.date,
                created_at=_utc_now(),
            )

        record.publish_record_id = request.publish_record_id
        record.render_id = request.render_id
        record.views = request.views
        record.likes = request.likes
        record.comments = request.comments
        record.shares = request.shares
        record.watch_time_seconds = request.watch_time_seconds
        record.avg_view_percentage = request.avg_view_percentage
        record.avg_view_duration_seconds = request.avg_view_duration_seconds
        merged_extra_metrics = dict(record.extra_metrics or {})
        if request.extra_metrics:
            merged_extra_metrics.update(request.extra_metrics)
        if request.audio_profile:
            merged_extra_metrics["audio_profile"] = request.audio_profile
        record.extra_metrics = merged_extra_metrics or None
        session.add(record)

        _audit_event(
            session,
            event_type="metrics_daily_manual_upsert",
            actor_user_id=request.actor,
            payload={
                "metrics_daily_id": str(record.id) if getattr(record, "id", None) else None,
                "platform_type": request.platform_type,
                "content_id": content_id,
                "date": str(request.date),
                "created": created,
                "publish_record_id": str(request.publish_record_id) if request.publish_record_id else None,
                "render_id": str(request.render_id) if request.render_id else None,
                "audio_profile": request.audio_profile,
            },
        )
        session.commit()
        return jsonable_encoder(
            {
                "created": created,
                "metrics_daily_id": record.id,
                "platform_type": record.platform_type,
                "content_id": record.content_id,
                "date": record.date,
                "views": record.views,
                "likes": record.likes,
                "comments": record.comments,
                "shares": record.shares,
                "audio_profile": (
                    record.extra_metrics.get("audio_profile")
                    if isinstance(record.extra_metrics, dict)
                    else None
                ),
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        session.close()


@app.get("/idea-candidates")
def list_idea_candidates(
    idea_batch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    similarity_status: Optional[str] = None,
    capability_status: Optional[str] = None,
    selected: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(IdeaCandidate)
        if idea_batch_id:
            stmt = stmt.where(IdeaCandidate.idea_batch_id == idea_batch_id)
        if status:
            stmt = stmt.where(IdeaCandidate.status == status)
        if similarity_status:
            stmt = stmt.where(IdeaCandidate.similarity_status == similarity_status)
        if capability_status:
            stmt = stmt.where(IdeaCandidate.capability_status == capability_status)
        if selected is not None:
            stmt = stmt.where(IdeaCandidate.selected == selected)
        stmt = stmt.order_by(desc(IdeaCandidate.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/ideas")
def list_ideas(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(Idea)
        if status:
            stmt = stmt.where(Idea.status == status)
        stmt = stmt.order_by(desc(Idea.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/ideas/blocked")
def list_blocked_ideas(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        rows = session.execute(
            select(Idea)
            .where(Idea.status == "blocked_by_gaps")
            .order_by(desc(Idea.created_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        payload: list[dict] = []
        for idea in rows:
            links = session.execute(
                select(DslGap.feature, DslGap.status)
                .join(IdeaGapLink, IdeaGapLink.dsl_gap_id == DslGap.id)
                .where(IdeaGapLink.idea_id == idea.id)
                .order_by(desc(DslGap.updated_at))
            ).all()
            payload.append(
                {
                    "id": str(idea.id),
                    "title": idea.title,
                    "status": idea.status,
                    "gaps": [{"feature": feature, "status": status} for feature, status in links],
                }
            )
        return jsonable_encoder(payload)
    finally:
        session.close()


@app.get("/idea-candidates/blocked")
def list_blocked_idea_candidates(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        rows = session.execute(
            select(IdeaCandidate)
            .where(IdeaCandidate.capability_status == "blocked_by_gaps")
            .order_by(desc(IdeaCandidate.created_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        payload: list[dict] = []
        for candidate in rows:
            links = session.execute(
                select(DslGap.feature, DslGap.status)
                .join(IdeaCandidateGapLink, IdeaCandidateGapLink.dsl_gap_id == DslGap.id)
                .where(IdeaCandidateGapLink.idea_candidate_id == candidate.id)
                .order_by(desc(DslGap.updated_at))
            ).all()
            payload.append(
                {
                    "id": str(candidate.id),
                    "title": candidate.title,
                    "status": candidate.capability_status,
                    "gaps": [{"feature": feature, "status": status} for feature, status in links],
                }
            )
        return jsonable_encoder(payload)
    finally:
        session.close()


@app.get("/idea-repo/sample")
def sample_idea_repo(limit: int = Query(3, ge=1, le=20)) -> List[dict]:
    session = SessionLocal()
    try:
        def _serialize_candidate(candidate: IdeaCandidate) -> dict:
            return {
                "id": str(candidate.id),
                "idea_batch_id": str(candidate.idea_batch_id),
                "title": candidate.title,
                "summary": candidate.summary,
                "what_to_expect": candidate.what_to_expect,
                "preview": candidate.preview,
                "generator_source": candidate.generator_source,
                "similarity_status": candidate.similarity_status,
                "capability_status": candidate.capability_status,
                "status": candidate.status,
                "selected": candidate.selected,
                "selected_at": candidate.selected_at,
                "selected_by": str(candidate.selected_by) if candidate.selected_by else None,
                "decision_at": candidate.decision_at,
                "created_at": candidate.created_at,
            }

        base_candidates = session.execute(
            select(IdeaCandidate).where(IdeaCandidate.status.in_(["new", "later"]))
        ).scalars().all()

        if not _dev_manual_flow_enabled():
            for candidate in base_candidates:
                if candidate.capability_status == "unverified":
                    verify_candidate_capability(session, idea_candidate_id=candidate.id)
            session.flush()

        stmt = select(IdeaCandidate).where(IdeaCandidate.status.in_(["new", "later"]))
        if not _dev_manual_flow_enabled():
            stmt = stmt.where(IdeaCandidate.capability_status == "feasible")
        stmt = stmt.order_by(func.random()).limit(limit)
        rows = session.execute(stmt).scalars().all()
        session.commit()
        return jsonable_encoder([_serialize_candidate(row) for row in rows])
    finally:
        session.close()


@app.post("/idea-repo/decide")
def decide_idea_repo(
    request: IdeaDecisionRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        if not request.decisions:
            raise HTTPException(status_code=400, detail="decisions_required")

        picked = [item for item in request.decisions if item.decision == "picked"]
        if len(picked) != 1:
            raise HTTPException(status_code=400, detail="exactly_one_picked_required")

        ids = [item.idea_candidate_id for item in request.decisions]
        stmt = select(IdeaCandidate).where(IdeaCandidate.id.in_(ids))
        candidates = session.execute(stmt).scalars().all()
        if len(candidates) != len(ids):
            raise HTTPException(status_code=404, detail="idea_candidate_not_found")

        by_id = {candidate.id: candidate for candidate in candidates}
        now = datetime.now(timezone.utc)

        picked_candidate = by_id[picked[0].idea_candidate_id]
        if picked_candidate.status == "picked":
            raise HTTPException(status_code=409, detail="already_picked")
        if (not _dev_manual_flow_enabled()) and picked_candidate.capability_status != "feasible":
            raise HTTPException(status_code=409, detail="candidate_not_feasible")

        picked_candidate.status = "picked"
        picked_candidate.selected = True
        picked_candidate.selected_at = now
        picked_candidate.decision_at = now

        if picked_candidate.idea is None:
            idea = Idea(
                idea_candidate_id=picked_candidate.id,
                title=picked_candidate.title,
                summary=picked_candidate.summary,
                what_to_expect=picked_candidate.what_to_expect,
                preview=picked_candidate.preview,
                idea_hash=_hash_idea(picked_candidate.title, picked_candidate.summary or ""),
                status="ready_for_gate",
                created_at=now,
            )
            session.add(idea)
            session.flush()
        else:
            idea = picked_candidate.idea
            if idea.status != "compiled":
                idea.status = "ready_for_gate"
            session.add(idea)

        for item in request.decisions:
            candidate = by_id[item.idea_candidate_id]
            if item.decision == "later":
                candidate.status = "later"
                candidate.decision_at = now
                session.add(
                    AuditEvent(
                        event_type="idea_decision",
                        source="ui",
                        occurred_at=now,
                        payload={"idea_candidate_id": str(candidate.id), "decision": "later"},
                    )
                )
            elif item.decision == "rejected":
                candidate.status = "rejected"
                candidate.decision_at = now
                candidate.selected = False
                session.add(
                    AuditEvent(
                        event_type="idea_decision",
                        source="ui",
                        occurred_at=now,
                        payload={"idea_candidate_id": str(candidate.id), "decision": "rejected"},
                    )
                )
                session.add(candidate)

        session.add(
            AuditEvent(
                event_type="idea_decision",
                source="ui",
                occurred_at=now,
                payload={
                    "idea_id": str(idea.id),
                    "idea_candidate_id": str(picked_candidate.id),
                    "decision": "picked",
                },
            )
        )
        session.commit()
        return jsonable_encoder({"idea_id": idea.id, "idea_candidate_id": picked_candidate.id})
    finally:
        session.close()


@app.post("/ideas/verify-capability")
def verify_capability(
    request: IdeaCapabilityVerifyRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        report = verify_idea_capability(
            session,
            idea_id=request.idea_id,
            dsl_version=request.dsl_version,
            language=request.language,
        )
        session.commit()
        return jsonable_encoder(report)
    finally:
        session.close()


@app.post("/ideas/verify-capability/batch")
def verify_capability_batch(
    request: IdeaCapabilityVerifyBatchRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        idea_ids = session.execute(
            select(Idea.id)
            .where(Idea.status == "unverified")
            .order_by(desc(Idea.created_at))
            .limit(request.limit)
        ).all()
        reports = [
            verify_idea_capability(
                session,
                idea_id=idea_id,
                dsl_version=request.dsl_version,
                language=request.language,
            )
            for (idea_id,) in idea_ids
        ]
        session.commit()
        return jsonable_encoder({"verified": len(reports), "reports": reports})
    finally:
        session.close()


@app.post("/idea-candidates/verify-capability")
def verify_candidate_capability_endpoint(
    request: IdeaCandidateCapabilityVerifyRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        report = verify_candidate_capability(
            session,
            idea_candidate_id=request.idea_candidate_id,
            dsl_version=request.dsl_version,
            language=request.language,
        )
        session.commit()
        return jsonable_encoder(report)
    finally:
        session.close()


@app.post("/idea-candidates/verify-capability/batch")
def verify_candidate_capability_batch(
    request: IdeaCandidateCapabilityVerifyBatchRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        candidate_ids = session.execute(
            select(IdeaCandidate.id)
            .where(IdeaCandidate.capability_status == "unverified")
            .order_by(desc(IdeaCandidate.created_at))
            .limit(request.limit)
        ).all()
        reports = [
            verify_candidate_capability(
                session,
                idea_candidate_id=candidate_id,
                dsl_version=request.dsl_version,
                language=request.language,
            )
            for (candidate_id,) in candidate_ids
        ]
        session.commit()
        return jsonable_encoder({"verified": len(reports), "reports": reports})
    finally:
        session.close()


@app.post("/idea-candidates/{candidate_id}/reset-capability")
def reset_candidate_capability(
    candidate_id: UUID,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        candidate = session.get(IdeaCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="idea_candidate_not_found")

        session.execute(
            delete(IdeaCandidateGapLink).where(
                IdeaCandidateGapLink.idea_candidate_id == candidate.id
            )
        )
        candidate.capability_status = "unverified"
        session.add(candidate)

        session.add(
            AuditEvent(
                event_type="idea_candidate_reset",
                source="ui",
                occurred_at=datetime.now(timezone.utc),
                payload={"idea_candidate_id": str(candidate.id), "action": "reset_capability"},
            )
        )
        session.commit()
        return jsonable_encoder({"id": candidate.id, "capability_status": candidate.capability_status})
    finally:
        session.close()


@app.post("/idea-candidates/{candidate_id}/capability")
def override_candidate_capability(
    candidate_id: UUID,
    request: IdeaCandidateCapabilityOverrideRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        candidate = session.get(IdeaCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="idea_candidate_not_found")

        session.execute(
            delete(IdeaCandidateGapLink).where(
                IdeaCandidateGapLink.idea_candidate_id == candidate.id
            )
        )
        candidate.capability_status = request.status
        session.add(candidate)

        session.add(
            AuditEvent(
                event_type="idea_candidate_capability_override",
                source="ui",
                occurred_at=datetime.now(timezone.utc),
                payload={
                    "idea_candidate_id": str(candidate.id),
                    "status": request.status,
                    "reason": request.reason,
                },
            )
        )
        session.commit()
        return jsonable_encoder({"id": candidate.id, "capability_status": candidate.capability_status})
    finally:
        session.close()


@app.post("/idea-candidates/{candidate_id}/delete")
def delete_candidate(
    candidate_id: UUID,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        candidate = session.get(IdeaCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="idea_candidate_not_found")
        if candidate.status == "picked":
            raise HTTPException(status_code=409, detail="candidate_already_picked")
        if candidate.idea is not None:
            animations_count = session.execute(
                select(func.count()).select_from(Animation).where(Animation.idea_id == candidate.idea.id)
            ).scalar_one()
            if animations_count > 0:
                raise HTTPException(status_code=409, detail="candidate_has_animations")
            session.delete(candidate.idea)

        deleted_id = candidate.id
        session.delete(candidate)

        session.add(
            AuditEvent(
                event_type="idea_candidate_delete",
                source="ui",
                occurred_at=datetime.now(timezone.utc),
                payload={"idea_candidate_id": str(deleted_id), "action": "hard_delete"},
            )
        )
        session.commit()
        return jsonable_encoder({"id": deleted_id, "status": "deleted"})
    finally:
        session.close()


@app.post("/ops/idea-candidates/cleanup-later")
def cleanup_later_candidates(
    request: LaterCleanupRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        max_age_days = request.max_age_days or _later_idea_max_age_days()
        now = _utc_now()
        cutoff = now - timedelta(days=max_age_days)
        candidates = session.execute(
            select(IdeaCandidate).where(IdeaCandidate.status == "later")
        ).scalars().all()

        expired: list[IdeaCandidate] = [
            candidate for candidate in candidates if _candidate_last_activity_at(candidate) < cutoff
        ]
        deleted = 0
        skipped = 0
        skipped_ids: list[str] = []
        deleted_ids: list[str] = []
        for candidate in expired:
            if candidate.idea is not None:
                animations_count = session.execute(
                    select(func.count()).select_from(Animation).where(Animation.idea_id == candidate.idea.id)
                ).scalar_one()
                if animations_count > 0:
                    skipped += 1
                    skipped_ids.append(str(candidate.id))
                    continue
                if not request.dry_run:
                    session.delete(candidate.idea)
            if not request.dry_run:
                session.delete(candidate)
            deleted += 1
            deleted_ids.append(str(candidate.id))

        _audit_event(
            session,
            event_type="idea_candidate_cleanup_later",
            actor_user_id=request.actor,
            payload={
                "max_age_days": max_age_days,
                "cutoff": cutoff.isoformat(),
                "dry_run": request.dry_run,
                "expired_count": len(expired),
                "deleted_count": deleted,
                "skipped_count": skipped,
                "skipped_ids": skipped_ids[:20],
            },
        )
        session.commit()
        return jsonable_encoder(
            {
                "max_age_days": max_age_days,
                "cutoff": cutoff,
                "dry_run": request.dry_run,
                "expired_count": len(expired),
                "deleted_count": deleted,
                "deleted_ids": deleted_ids,
                "skipped_count": skipped,
                "skipped_ids": skipped_ids,
            }
        )
    finally:
        session.close()


@app.post("/idea-candidates/{candidate_id}/undo-decision")
def undo_candidate_decision(
    candidate_id: UUID,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        candidate = session.get(IdeaCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="idea_candidate_not_found")
        if candidate.status == "new":
            raise HTTPException(status_code=409, detail="candidate_already_new")

        if candidate.status == "picked" and candidate.idea is not None:
            animations_count = session.execute(
                select(func.count()).select_from(Animation).where(Animation.idea_id == candidate.idea.id)
            ).scalar_one()
            if animations_count > 0:
                raise HTTPException(status_code=409, detail="idea_already_used")
            session.delete(candidate.idea)

        candidate.status = "new"
        candidate.selected = False
        candidate.selected_at = None
        candidate.selected_by = None
        candidate.decision_at = None
        candidate.decision_by = None
        session.add(candidate)

        session.add(
            AuditEvent(
                event_type="idea_candidate_undo",
                source="ui",
                occurred_at=datetime.now(timezone.utc),
                payload={"idea_candidate_id": str(candidate.id), "action": "undo_decision"},
            )
        )
        session.commit()
        return jsonable_encoder({"id": candidate.id, "status": candidate.status})
    finally:
        session.close()


@app.get("/dsl-gaps")
def list_dsl_gaps(
    status: Optional[str] = None,
    dsl_version: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(DslGap)
        if status:
            stmt = stmt.where(DslGap.status == status)
        if dsl_version:
            stmt = stmt.where(DslGap.dsl_version == dsl_version)
        stmt = stmt.order_by(desc(DslGap.updated_at), desc(DslGap.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/dsl/versions")
def list_dsl_versions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(DslVersion).order_by(desc(DslVersion.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        versions: list[dict] = []
        for row in rows:
            introduced = session.execute(
                select(func.count()).select_from(DslGap).where(DslGap.dsl_version == row.version)
            ).scalar_one()
            implemented = session.execute(
                select(func.count())
                .select_from(DslGap)
                .where(DslGap.implemented_in_version == row.version)
            ).scalar_one()
            versions.append(
                {
                    "id": row.id,
                    "version": row.version,
                    "is_active": row.is_active,
                    "notes": row.notes,
                    "created_at": row.created_at,
                    "introduced_gaps": int(introduced),
                    "implemented_gaps": int(implemented),
                }
            )
        return jsonable_encoder(versions)
    finally:
        session.close()


@app.post("/dsl-gaps/{gap_id}/status")
def update_dsl_gap_status(
    gap_id: UUID,
    request: DslGapStatusRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        gap = session.get(DslGap, gap_id)
        if gap is None:
            raise HTTPException(status_code=404, detail="dsl_gap_not_found")

        now = datetime.now(timezone.utc)
        gap.status = request.status
        gap.updated_at = now
        if request.status == "implemented":
            if not request.implemented_in_dsl_version:
                raise HTTPException(status_code=400, detail="implemented_in_dsl_version_required")
            gap.implemented_in_version = request.implemented_in_dsl_version
            gap.resolved_at = now
            gap.resolved_by = None
            _activate_dsl_version(
                session,
                version=request.implemented_in_dsl_version,
                notes=request.notes,
            )
        session.add(gap)

        dsl_version = request.implemented_in_dsl_version or gap.dsl_version
        reverify_candidates = reverify_candidates_for_gap(
            session,
            dsl_gap_id=gap.id,
            dsl_version=dsl_version,
        )
        reverify_ideas = reverify_ideas_for_gap(
            session,
            dsl_gap_id=gap.id,
            dsl_version=dsl_version,
        )

        session.commit()
        return jsonable_encoder(
            {
                "gap": gap,
                "reverify_candidates": reverify_candidates,
                "reverify_ideas": reverify_ideas,
            }
        )
    finally:
        session.close()


@app.post("/ideas/{idea_id}/compile-dsl")
def compile_idea_dsl(
    idea_id: UUID,
    req: IdeaCompileRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        idea = session.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="idea_not_found")
        out_dir = Path(req.out_root) / f"idea-{idea.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / "dsl.yaml"
        result = compile_idea_to_dsl(
            idea=idea,
            template_path=Path(req.dsl_template),
            target_path=target_path,
            animation_code=uuid4().hex,
            max_attempts=req.max_attempts,
            max_repairs=req.max_repairs,
        )
        idea.status = "compiled"
        session.add(idea)
        session.commit()
        return {
            "idea_id": idea.id,
            "dsl_path": str(target_path),
            "dsl_hash": result.dsl_hash,
            "compiler_meta": result.compiler_meta,
            "validation_report": result.validation_report,
        }
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        session.close()


@app.get("/idea-embeddings")
def list_idea_embeddings(
    idea_candidate_id: Optional[UUID] = None,
    idea_id: Optional[UUID] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    version: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(IdeaEmbedding)
        if idea_candidate_id:
            stmt = stmt.where(IdeaEmbedding.idea_candidate_id == idea_candidate_id)
        if idea_id:
            stmt = stmt.where(IdeaEmbedding.idea_id == idea_id)
        if provider:
            stmt = stmt.where(IdeaEmbedding.provider == provider)
        if model:
            stmt = stmt.where(IdeaEmbedding.model == model)
        if version:
            stmt = stmt.where(IdeaEmbedding.version == version)
        stmt = stmt.order_by(desc(IdeaEmbedding.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.post("/idea-candidates/generate")
def generate_idea_candidates(
    request: IdeaCandidateGenerateRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        mode = request.mode
        drafts: list[IdeaDraft] = []
        if mode == "llm":
            if request.limit is None:
                raise HTTPException(status_code=400, detail="limit_required_for_llm")
            drafts = generate_ideas(
                source="openai",
                limit=request.limit,
                prompt=request.prompt or "",
                language=request.language,
            )
        elif mode == "text":
            base_text = (request.text or "").strip()
            title = (request.title or "").strip()
            summary = (request.summary or "").strip()
            if not (base_text or title or summary):
                raise HTTPException(status_code=400, detail="text_or_title_required")
            if not title:
                title = base_text.splitlines()[0][:120] if base_text else summary[:120]
            if not summary:
                summary = base_text if base_text else title
            drafts = [
                IdeaDraft(
                    title=title,
                    summary=summary,
                    what_to_expect=(request.what_to_expect or "").strip(),
                    preview=(request.preview or "").strip(),
                    source="manual",
                    generation_meta={"mode": "text"},
                    idea_hash=_hash_idea(title, summary),
                )
            ]
        elif mode == "file":
            content = (request.file_content or "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="file_content_required")
            parsed = parse_ideas_text(content)
            drafts = [
                IdeaDraft(
                    title=item.title,
                    summary=item.summary,
                    what_to_expect=item.what_to_expect,
                    preview=item.preview,
                    source="file",
                    generation_meta={"mode": "file", "file_name": request.file_name},
                    idea_hash=_hash_idea(item.title, item.summary),
                )
                for item in parsed
            ]
        else:
            raise HTTPException(status_code=400, detail="unsupported_mode")

        existing_hashes = {
            str(value)
            for (value,) in session.execute(select(Idea.idea_hash).where(Idea.idea_hash.is_not(None))).all()
            if value
        }
        skip_summary: dict[str, int] = {}
        skip_examples: list[dict[str, str]] = []
        for draft in drafts:
            reason: str | None = None
            if draft.idea_hash and draft.idea_hash in existing_hashes:
                reason = "duplicate_hash"
            elif len((draft.title or "").strip()) < 3:
                reason = "invalid_title_too_short"
            elif len((draft.summary or "").strip()) < 20:
                reason = "invalid_summary_too_short"
            elif not _is_valid(draft):
                reason = "invalid_draft"
            if reason:
                skip_summary[reason] = skip_summary.get(reason, 0) + 1
                if len(skip_examples) < 5:
                    skip_examples.append({"title": (draft.title or "").strip()[:120], "reason": reason})

        if not drafts:
            return jsonable_encoder(
                {
                    "created": 0,
                    "skipped": 0,
                    "idea_candidate_ids": [],
                    "skip_summary": skip_summary,
                    "skip_examples": skip_examples,
                }
            )

        idea_batch = IdeaBatch(
            run_date=date.today(),
            window_id=datetime.now(timezone.utc).strftime("ui-%Y%m%d-%H%M%S"),
            source="manual",
            created_at=datetime.now(timezone.utc),
        )
        session.add(idea_batch)
        session.flush()

        embedder = EmbeddingService(EmbeddingConfig(provider="sklearn-hash"))
        created = save_ideas(
            session,
            drafts,
            embedder,
            similarity_threshold=0.97,
            idea_batch_id=idea_batch.id,
        )
        session.commit()
        return jsonable_encoder(
            {
                "created": len(created),
                "skipped": len(drafts) - len(created),
                "idea_batch_id": str(idea_batch.id),
                "idea_candidate_ids": [str(item.id) for item in created],
                "skip_summary": skip_summary,
                "skip_examples": skip_examples,
            }
        )
    finally:
        session.close()


@app.get("/pipeline/summary")
def pipeline_summary(
    limit: int = Query(10, ge=1, le=200),
) -> dict:
    session = SessionLocal()
    try:
        summary_rows = session.execute(
            select(Job.status, func.count()).group_by(Job.status)
        ).all()
        summary = {status: count for status, count in summary_rows}

        jobs = session.execute(
            select(Job).order_by(desc(Job.created_at)).limit(limit)
        ).scalars().all()
        return {
            "summary": summary,
            "jobs": jsonable_encoder(jobs),
            "worker": _worker_state(),
        }
    finally:
        session.close()


@app.get("/llm/metrics")
def llm_metrics(_guard: None = Depends(_require_operator)) -> dict:
    return jsonable_encoder(get_mediator().get_metrics_snapshot())


@app.get("/pipeline/jobs")
def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(Job)
        if status:
            stmt = stmt.where(Job.status == status)
        if job_type:
            stmt = stmt.where(Job.job_type == job_type)
        stmt = stmt.order_by(desc(Job.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/animations")
def list_animations(
    status: Optional[str] = None,
    pipeline_stage: Optional[str] = None,
    idea_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        latest_render = (
            select(Render.animation_id, func.max(Render.created_at).label("max_created"))
            .group_by(Render.animation_id)
            .subquery()
        )
        latest_qc = (
            select(QCDecision.animation_id, func.max(QCDecision.decided_at).label("max_decided"))
            .group_by(QCDecision.animation_id)
            .subquery()
        )

        stmt = (
            select(Animation, Render, QCDecision)
            .outerjoin(latest_render, latest_render.c.animation_id == Animation.id)
            .outerjoin(
                Render,
                and_(
                    Render.animation_id == Animation.id,
                    Render.created_at == latest_render.c.max_created,
                ),
            )
            .outerjoin(latest_qc, latest_qc.c.animation_id == Animation.id)
            .outerjoin(
                QCDecision,
                and_(
                    QCDecision.animation_id == Animation.id,
                    QCDecision.decided_at == latest_qc.c.max_decided,
                ),
            )
        )
        if status:
            stmt = stmt.where(Animation.status == status)
        if pipeline_stage:
            stmt = stmt.where(Animation.pipeline_stage == pipeline_stage)
        if idea_id:
            stmt = stmt.where(Animation.idea_id == idea_id)

        stmt = stmt.order_by(desc(Animation.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).all()
        return [_animation_row(anim, render, qc) for anim, render, qc in rows]
    finally:
        session.close()


@app.get("/idea-gate/candidates")
def list_idea_gate_candidates(
    idea_batch_id: Optional[UUID] = None,
    similarity_status: Optional[str] = None,
    selected: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    return list_idea_candidates(
        idea_batch_id=idea_batch_id,
        similarity_status=similarity_status,
        selected=selected,
        limit=limit,
        offset=offset,
    )


@app.get("/renders/{render_id}/artifacts")
def list_render_artifacts(render_id: UUID) -> List[dict]:
    session = SessionLocal()
    try:
        stmt = (
            select(Artifact)
            .where(Artifact.render_id == render_id)
            .order_by(desc(Artifact.created_at))
        )
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/publish-records")
def list_publish_records(
    render_id: UUID | None = None,
    animation_id: UUID | None = None,
    platform_type: Literal["youtube", "tiktok"] | None = None,
    status: Literal["queued", "uploading", "published", "failed", "manual_confirmed"] | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    limit, offset = _paginate(limit, offset)
    session = SessionLocal()
    try:
        stmt = select(PublishRecord)
        if animation_id:
            stmt = stmt.join(Render, Render.id == PublishRecord.render_id).where(Render.animation_id == animation_id)
        if render_id:
            stmt = stmt.where(PublishRecord.render_id == render_id)
        if platform_type:
            stmt = stmt.where(PublishRecord.platform_type == platform_type)
        if status:
            stmt = stmt.where(PublishRecord.status == status)
        stmt = stmt.order_by(desc(PublishRecord.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
    finally:
        session.close()


@app.get("/publish/connectors/status")
def publish_connectors_status(_guard: None = Depends(_require_operator)) -> dict:
    return jsonable_encoder({"updated_at": _utc_now(), "connectors": _publish_connector_status()})


@app.get("/publish/readiness-summary")
def publish_readiness_summary(_guard: None = Depends(_require_operator)) -> dict:
    payload, error = _read_publish_readiness_summary()
    if error == "missing":
        raise HTTPException(status_code=404, detail="publish_readiness_summary_missing")
    if error == "invalid" or payload is None:
        raise HTTPException(status_code=500, detail="publish_readiness_summary_invalid")
    return jsonable_encoder(payload)


@app.get("/artifacts/{artifact_id}/file")
def get_artifact_file(artifact_id: UUID):
    session = SessionLocal()
    try:
        artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="artifact_not_found")

        storage_path = Path(artifact.storage_path).expanduser().resolve()
        if not storage_path.exists():
            raise HTTPException(status_code=404, detail="artifact_missing")

        base_dir = _artifact_base_dir()
        try:
            storage_path.relative_to(base_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="artifact_outside_allowed_dir")

        media_type = None
        if artifact.artifact_type == "video":
            media_type = "video/mp4"
        elif artifact.artifact_type == "metadata":
            media_type = "application/json"

        return FileResponse(path=str(storage_path), media_type=media_type)
    finally:
        session.close()


@app.get("/godot/manual-file")
def get_manual_godot_file(path: str = Query(..., min_length=1)):
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="file_not_found")
    base_dir = _manual_godot_root()
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="file_outside_manual_godot_root")

    suffix = file_path.suffix.lower()
    media_type = None
    if suffix == ".mp4":
        media_type = "video/mp4"
    elif suffix == ".ogv":
        media_type = "video/ogg"
    elif suffix == ".avi":
        media_type = "video/x-msvideo"
    elif suffix == ".json":
        media_type = "application/json"
    elif suffix == ".log":
        media_type = "text/plain; charset=utf-8"
    return FileResponse(path=str(file_path), media_type=media_type)


@app.get("/ops/godot/manual-runs")
def list_godot_manual_runs(
    limit: int = Query(20, ge=1, le=100),
    step: Literal["compile", "validate", "preview", "render"] | None = Query(default=None),
    script_path: str | None = Query(default=None),
    _guard: None = Depends(_require_operator),
) -> list[dict]:
    normalized_script = None
    if script_path:
        normalized_script = str(Path(script_path).expanduser().resolve())
    return _read_manual_godot_history(limit=limit, step=step, script_path=normalized_script)


@app.post("/ops/enqueue")
def ops_enqueue(request: EnqueueRequest, _guard: None = Depends(_require_operator)) -> dict:
    from pipeline.queue import enqueue_pipeline

    if request.idea_gate and request.idea_id is None:
        raise HTTPException(status_code=400, detail="idea_selection_required")

    result = enqueue_pipeline(
        request.dsl_template,
        request.out_root,
        request.idea_gate,
        str(request.idea_id) if request.idea_id else None,
    )
    return jsonable_encoder(result)


@app.post("/ops/rerun")
def ops_rerun(request: RerunRequest, _guard: None = Depends(_require_operator)) -> dict:
    from pipeline.queue import enqueue_render

    result = enqueue_render(str(request.animation_id), request.out_root)
    return jsonable_encoder(result)


@app.post("/ops/cleanup-jobs")
def ops_cleanup_jobs(request: CleanupRequest, _guard: None = Depends(_require_operator)) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=request.older_min)
    session = SessionLocal()
    try:
        stmt = select(Job).where(and_(Job.status == "running", Job.updated_at < cutoff))
        jobs = session.execute(stmt).scalars().all()
        for job in jobs:
            job.status = "failed"
            job.error_payload = {"message": f"auto-cleanup: running > {request.older_min} min"}
            job.updated_at = datetime.now(timezone.utc)
            session.add(job)
        session.commit()
        return {"marked_failed": len(jobs)}
    finally:
        session.close()


@app.post("/ops/qc-decide")
def ops_qc_decide(
    request: QcDecisionCreateRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        animation = session.get(Animation, request.animation_id)
        if animation is None:
            raise HTTPException(status_code=404, detail="animation_not_found")
        _validate_qc_decision_request(request)

        checklist = _get_or_create_qc_checklist(session)
        now = _utc_now()
        decision = QCDecision(
            animation_id=animation.id,
            checklist_version_id=checklist.id,
            result=request.result,
            decision_payload=request.decision_payload,
            notes=(request.notes or "").strip() or None,
            decided_by=request.decided_by,
            decided_at=now,
            created_at=now,
        )
        session.add(decision)
        session.flush()

        _apply_qc_result(animation, request.result)
        animation.updated_at = now
        session.add(animation)

        session.add(
            AuditEvent(
                event_type="qc_decision",
                source="ui",
                actor_user_id=request.decided_by,
                occurred_at=now,
                payload={
                    "animation_id": str(animation.id),
                    "qc_decision_id": str(decision.id),
                    "result": request.result,
                    "notes": (request.notes or "").strip() or None,
                },
            )
        )
        session.commit()
        return jsonable_encoder(
            {
                "animation_id": animation.id,
                "qc_decision_id": decision.id,
                "result": decision.result,
                "animation_status": animation.status,
                "pipeline_stage": animation.pipeline_stage,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        session.close()


@app.post("/ops/publish-record")
def ops_publish_record(
    request: PublishRecordCreateRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        _validate_publish_record_request(request)
        render = session.get(Render, request.render_id)
        if render is None:
            raise HTTPException(status_code=404, detail="render_not_found")
        animation = session.get(Animation, render.animation_id)
        if animation is None:
            raise HTTPException(status_code=404, detail="animation_not_found")

        now = _utc_now()
        record = PublishRecord(
            render_id=render.id,
            platform_type=request.platform,
            status=request.status,
            content_id=(request.content_id or "").strip() or None,
            url=(request.url or "").strip() or None,
            scheduled_for=request.scheduled_for,
            published_at=request.published_at,
            error_payload={"message": request.error} if request.error else None,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()

        _apply_publish_status(animation, request.status)
        animation.updated_at = now
        session.add(animation)

        session.add(
            AuditEvent(
                event_type="publish_record",
                source="ui",
                actor_user_id=request.actor,
                occurred_at=now,
                payload={
                    "render_id": str(render.id),
                    "animation_id": str(animation.id),
                    "publish_record_id": str(record.id),
                    "platform": request.platform,
                    "status": request.status,
                },
            )
        )
        session.commit()
        return jsonable_encoder(
            {
                "publish_record_id": record.id,
                "render_id": render.id,
                "animation_id": animation.id,
                "platform": record.platform_type,
                "status": record.status,
                "animation_status": animation.status,
                "pipeline_stage": animation.pipeline_stage,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        session.close()


@app.post("/ops/godot/compile-gdscript")
def ops_godot_compile_gdscript(
    request: GodotManualCompileRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        idea = session.get(Idea, request.idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="idea_not_found")
        out_dir = Path(request.out_root).expanduser().resolve() / f"idea-{idea.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        script_path = out_dir / "script.gd"
        result = compile_idea_to_gdscript(
            idea=idea,
            target_path=script_path,
            max_attempts=request.max_attempts,
            max_repairs=request.max_repairs,
            validate=request.validate_after_compile,
            validate_seconds=request.validate_seconds,
            max_nodes=request.max_nodes,
        )
        payload = {
            "idea_id": idea.id,
            "script_path": str(script_path),
            "script_exists": script_path.exists(),
            "script_hash": result.script_hash,
            "compiler_meta": result.compiler_meta,
            "validation_report": result.validation_report,
        }
        _audit_event(
            session,
            event_type="godot_manual_compile",
            actor_user_id=request.actor,
            payload={
                "idea_id": str(idea.id),
                "script_path": str(script_path),
                "script_hash": result.script_hash,
            },
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="compile",
                ok=True,
                actor_user_id=request.actor,
                idea_id=idea.id,
                payload=payload,
            )
        )
        session.commit()
        return jsonable_encoder(payload)
    except HTTPException as exc:
        session.rollback()
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="compile",
                ok=False,
                actor_user_id=request.actor,
                idea_id=request.idea_id,
                error=str(exc.detail),
            )
        )
        raise
    except Exception as exc:
        session.rollback()
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="compile",
                ok=False,
                actor_user_id=request.actor,
                idea_id=request.idea_id,
                error=str(exc),
            )
        )
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        session.close()


def _ops_godot_run_mode(
    *,
    mode: Literal["validate", "preview", "render"],
    request: GodotManualRunRequest,
) -> dict:
    script_path = Path(request.script_path).expanduser().resolve()
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="script_not_found")
    if script_path.suffix != ".gd":
        raise HTTPException(status_code=400, detail="script_must_be_gd")

    out_path: Path | None = None
    if mode in {"preview", "render"}:
        if request.out_path:
            out_path = Path(request.out_path).expanduser().resolve()
        else:
            manual_root = _manual_godot_root()
            try:
                script_path.parent.relative_to(manual_root)
                base_dir = script_path.parent
            except ValueError:
                base_dir = manual_root / script_path.stem
            out_path = base_dir / ("preview.mp4" if mode == "preview" else "final.mp4")

    result = _run_godot_manual_step(
        mode=mode,
        script_path=script_path,
        seconds=request.seconds,
        fps=request.fps,
        max_nodes=request.max_nodes,
        out_path=out_path,
        scale=request.scale if mode == "preview" else None,
    )
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result)
    return result


def _resolve_target_runtime_s(runtime_override_s: float | None = None) -> float:
    if runtime_override_s is not None:
        return float(runtime_override_s)
    raw = getenv("OPERATOR_TARGET_RUNTIME_S", "60") or "60"
    try:
        value = float(raw)
    except ValueError:
        value = 60.0
    return max(1.0, min(value, 300.0))


def _intent_recommendation(
    *,
    estimate: dict | None,
    target_duration_s: float,
    scout_seconds: float,
    tail_seconds: float,
) -> dict:
    estimate_payload = estimate if isinstance(estimate, dict) else {}
    reached = bool(estimate_payload.get("reached")) if estimate_payload else False
    effect_time = (
        float(estimate_payload.get("effect_time_s", -1.0) or -1.0) if estimate_payload else -1.0
    )
    progress = float(estimate_payload.get("progress", 0.0) or 0.0) if estimate_payload else 0.0
    support = bool(estimate_payload.get("support")) if estimate_payload else False

    if reached and effect_time >= 0.0:
        recommended_sim_duration_s = max(1.0, min(scout_seconds, effect_time + tail_seconds))
        confidence = max(0.2, min(1.0, progress if support else 0.6))
        method = "progress_threshold"
        intent_status = "pass"
        blocking_reason = None
    else:
        recommended_sim_duration_s = max(1.0, min(scout_seconds, target_duration_s))
        confidence = 0.2
        method = "fallback_target_duration"
        intent_status = "blocked"
        blocking_reason = "intent_not_reached_in_scout_horizon"

    speed_factor = recommended_sim_duration_s / target_duration_s if target_duration_s > 0 else 1.0
    return {
        "intent_reached": reached,
        "intent_reached_at_s": effect_time if reached and effect_time >= 0.0 else None,
        "intent_progress": progress if support else None,
        "recommended_sim_duration_s": recommended_sim_duration_s,
        "recommended_speed_factor": speed_factor,
        "confidence": confidence,
        "method": method,
        "intent_status": intent_status,
        "blocking_reason": blocking_reason,
    }


def _later_idea_max_age_days() -> int:
    raw = getenv("OPERATOR_LATER_MAX_AGE_DAYS", "30") or "30"
    try:
        value = int(raw)
    except ValueError:
        value = 30
    return max(1, min(value, 3650))


def _candidate_last_activity_at(candidate: IdeaCandidate) -> datetime:
    return candidate.decision_at or candidate.created_at or _utc_now()


def _publish_connector_status() -> dict:
    youtube_ready = bool(
        (getenv("YOUTUBE_CLIENT_ID", "") or "").strip()
        and (getenv("YOUTUBE_CLIENT_SECRET", "") or "").strip()
        and (
            (getenv("YOUTUBE_REFRESH_TOKEN", "") or "").strip()
            or (getenv("YOUTUBE_ACCESS_TOKEN", "") or "").strip()
        )
    )
    tiktok_ready = bool(
        (getenv("TIKTOK_CLIENT_KEY", "") or "").strip()
        and (getenv("TIKTOK_CLIENT_SECRET", "") or "").strip()
        and (
            (getenv("TIKTOK_ACCESS_TOKEN", "") or "").strip()
            or (getenv("TIKTOK_REFRESH_TOKEN", "") or "").strip()
        )
    )
    return {
        "youtube": {
            "ready": youtube_ready,
            "mode": "api" if youtube_ready else "manual_fallback",
        },
        "tiktok": {
            "ready": tiktok_ready,
            "mode": "api" if tiktok_ready else "manual_fallback",
        },
    }


def _ffmpeg_timeout_s() -> int:
    raw = getenv("FFMPEG_TIMEOUT_S", "120") or "120"
    try:
        timeout = int(raw)
    except ValueError:
        timeout = 120
    return max(10, min(timeout, 900))


def _escape_drawtext_text(text: str) -> str:
    value = text.replace("\\", "\\\\")
    for token in [":", "'", "%", ","]:
        value = value.replace(token, f"\\{token}")
    return value


@lru_cache(maxsize=1)
def _ffmpeg_supported_filters() -> set[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return set()
    try:
        completed = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return set()
    payload = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    filters: set[str] = set()
    for line in payload.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] and all(ch in ".TSC|" for ch in parts[0]):
            filters.add(parts[1].strip())
    return filters


def _ffmpeg_has_filter(name: str) -> bool:
    return name in _ffmpeg_supported_filters()


def _video_dimensions(input_path: Path) -> tuple[int, int]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 1080, 1920
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(input_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        data = json.loads(completed.stdout or "{}")
        streams = data.get("streams") or []
        if streams:
            width = int(streams[0].get("width") or 1080)
            height = int(streams[0].get("height") or 1920)
            return max(64, width), max(64, height)
    except Exception:
        pass
    return 1080, 1920


def _run_intro_overlay_ffmpeg_image_fallback(
    *,
    ffmpeg: str,
    input_path: Path,
    out_path: Path,
    text: str,
    duration_s: float,
    font_size: int,
) -> dict:
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        return {"ok": False, "error": "drawtext_missing_and_magick_not_found"}
    width, height = _video_dimensions(input_path)
    overlay_h = max(96, int(height * 0.18))
    enable_expr = f"between(t\\,0\\,{duration_s:.2f})"
    font_file = (getenv("INTRO_OVERLAY_FONT_FILE", "") or "").strip()

    with tempfile.TemporaryDirectory(prefix="shortlab-intro-") as tmpdir:
        text_image_path = Path(tmpdir) / "intro-text.png"
        magick_cmd = [
            magick,
            "-size",
            f"{width}x{overlay_h}",
            "-background",
            "none",
            "-fill",
            "white",
            "-stroke",
            "black",
            "-strokewidth",
            "2",
            "-gravity",
            "center",
            "-pointsize",
            str(font_size),
        ]
        if font_file:
            magick_cmd.extend(["-font", font_file])
        magick_cmd.extend([f"caption:{text}", str(text_image_path)])
        try:
            magick_run = subprocess.run(
                magick_cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=_ffmpeg_timeout_s(),
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "error": "magick_timeout",
                "stdout": (exc.stdout or "").strip()[-8000:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "").strip()[-8000:] if isinstance(exc.stderr, str) else "",
                "out_exists": out_path.exists(),
                "out_path": str(out_path),
            }
        if magick_run.returncode != 0 or not text_image_path.exists():
            return {
                "ok": False,
                "error": "magick_text_image_failed",
                "exit_code": magick_run.returncode,
                "stdout": (magick_run.stdout or "").strip()[-8000:],
                "stderr": (magick_run.stderr or "").strip()[-8000:],
                "out_exists": out_path.exists(),
                "out_path": str(out_path),
            }

        cmd = [
            ffmpeg,
            "-y",
            "-nostdin",
            "-i",
            str(input_path),
            "-loop",
            "1",
            "-i",
            str(text_image_path),
            "-filter_complex",
            (
                f"[0:v]drawbox=x=0:y=0:w=iw:h=ih*0.18:color=black@0.45:t=fill:enable={enable_expr}[base];"
                f"[base][1:v]overlay=x=(W-w)/2:y=H*0.06:enable={enable_expr}"
            ),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "copy",
            "-shortest",
            str(out_path),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=_ffmpeg_timeout_s(),
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "error": "ffmpeg_timeout",
                "stdout": (exc.stdout or "").strip()[-8000:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "").strip()[-8000:] if isinstance(exc.stderr, str) else "",
                "out_exists": out_path.exists(),
                "out_path": str(out_path),
                "fallback": "magick_overlay",
            }
        return {
            "ok": completed.returncode == 0 and out_path.exists(),
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "").strip()[-8000:],
            "stderr": (completed.stderr or "").strip()[-8000:],
            "out_exists": out_path.exists(),
            "out_path": str(out_path),
            "fallback": "magick_overlay",
        }


def _build_intro_text_from_idea(idea: Idea | None, language: str) -> str:
    if idea is None:
        return ""
    title = (idea.title or "").strip()
    summary = (idea.summary or "").strip()
    if language == "pl":
        if title:
            return f"Zasada animacji: {title}"
        if summary:
            return f"Co zobaczysz: {summary}"
        return "Krotka animacja z jasna zasada."
    if title:
        return f"Animation rule: {title}"
    if summary:
        return f"What you will see: {summary}"
    return "A short animation with a clear rule."


def _sanitize_intro_text(*, text: str, language: str, max_chars: int) -> str:
    value = re.sub(r"\s+", " ", (text or "")).strip()
    if language == "en":
        had_ascii = bool(re.search(r"[A-Za-z0-9]", value))
        rule_match = re.match(r"^\s*zasada animacji\s*:\s*(.+)$", value, flags=re.IGNORECASE)
        what_match = re.match(r"^\s*co zobaczysz\s*:\s*(.+)$", value, flags=re.IGNORECASE)
        if rule_match:
            value = f"Animation rule: {rule_match.group(1).strip()}"
        elif what_match:
            value = f"What you will see: {what_match.group(1).strip()}"
        value = value.translate(str.maketrans({"ł": "l", "Ł": "L"}))
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^A-Za-z0-9 .,!?;:'\"()/+-]", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        if not value or (not had_ascii and not rule_match and not what_match):
            value = "A short animation with a clear rule."
    if len(value) > max_chars:
        value = value[:max_chars].rstrip()
    return value


def _translate_intro_text_to_en(
    *,
    text: str,
    max_chars: int,
) -> tuple[str | None, dict | None]:
    value = re.sub(r"\s+", " ", (text or "")).strip()
    if not value:
        return None, None

    translate_enabled = (getenv("INTRO_EN_TRANSLATE_ENABLED", "1") or "1").strip() == "1"
    if not translate_enabled:
        return None, {"attempted": False, "reason": "disabled_by_env"}

    try:
        payload, meta = get_mediator().generate_json(
            task_type="intro_translate",
            system_prompt=(
                "Translate short video intro overlay text to natural, concise English."
                " Keep intent, keep it short, and avoid emojis/hashtags."
            ),
            user_prompt=(
                f"Source text:\n{value}\n\n"
                "Output requirements:\n"
                "- One sentence.\n"
                f"- Max {max_chars} characters.\n"
                "- No extra commentary.\n"
            ),
            json_schema={
                "type": "object",
                "properties": {
                    "intro_text_en": {"type": "string"},
                },
                "required": ["intro_text_en"],
                "additionalProperties": False,
            },
            max_tokens=120,
            temperature=0.2,
        )
        translated = str(payload.get("intro_text_en", "")).strip()
        if not translated:
            return None, {
                "attempted": True,
                "status": "empty_result",
                "provider": meta.get("provider"),
                "model": meta.get("model"),
            }
        if len(translated) > max_chars:
            translated = translated[:max_chars].rstrip()
        return translated, {
            "attempted": True,
            "status": "translated",
            "provider": meta.get("provider"),
            "model": meta.get("model"),
        }
    except Exception as exc:
        return None, {
            "attempted": True,
            "status": "fallback",
            "error": str(exc)[:240],
        }


def _run_intro_overlay_ffmpeg(
    *,
    input_path: Path,
    out_path: Path,
    text: str,
    duration_s: float,
    font_size: int,
) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "error": "ffmpeg_not_found"}

    if not _ffmpeg_has_filter("drawtext"):
        return _run_intro_overlay_ffmpeg_image_fallback(
            ffmpeg=ffmpeg,
            input_path=input_path,
            out_path=out_path,
            text=text,
            duration_s=duration_s,
            font_size=font_size,
        )

    enable_expr = f"between(t,0,{duration_s:.2f})"
    escaped_text = _escape_drawtext_text(text)
    filter_parts = [
        f"drawbox=x=0:y=0:w=iw:h=ih*0.18:color=black@0.45:t=fill:enable='{enable_expr}'",
    ]
    drawtext = (
        f"drawtext=text='{escaped_text}'"
        f":x=(w-text_w)/2:y=h*0.06:fontsize={font_size}"
        ":fontcolor=white:borderw=2:bordercolor=black@0.7"
        f":enable='{enable_expr}'"
    )
    font_file = (getenv("INTRO_OVERLAY_FONT_FILE", "") or "").strip()
    if font_file:
        drawtext += f":fontfile='{_escape_drawtext_text(font_file)}'"
    filter_parts.append(drawtext)
    vf = ",".join(filter_parts)

    cmd = [
        ffmpeg,
        "-y",
        "-nostdin",
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "copy",
        str(out_path),
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_ffmpeg_timeout_s(),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": "ffmpeg_timeout",
            "stdout": (exc.stdout or "").strip()[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip()[-8000:] if isinstance(exc.stderr, str) else "",
            "out_exists": out_path.exists(),
            "out_path": str(out_path),
        }
    return {
        "ok": completed.returncode == 0 and out_path.exists(),
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-8000:],
        "stderr": (completed.stderr or "").strip()[-8000:],
        "out_exists": out_path.exists(),
        "out_path": str(out_path),
    }


def _run_audio_mix_ffmpeg(
    *,
    input_path: Path,
    out_path: Path,
    music_path: Path | None,
    sfx_path: Path | None,
    keep_source_audio: bool,
    music_gain_db: float,
    sfx_gain_db: float,
    normalize_loudness: bool,
    target_lufs: float,
    true_peak_db: float,
) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "error": "ffmpeg_not_found"}

    cmd = [ffmpeg, "-y", "-nostdin", "-i", str(input_path)]
    input_index = 1
    music_index: int | None = None
    sfx_index: int | None = None
    if music_path is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])
        music_index = input_index
        input_index += 1
    if sfx_path is not None:
        cmd.extend(["-i", str(sfx_path)])
        sfx_index = input_index

    label_index = 0
    filters: list[str] = []
    mix_inputs: list[str] = []
    if keep_source_audio:
        label = f"s{label_index}"
        label_index += 1
        filters.append(f"[0:a]anull[{label}]")
        mix_inputs.append(f"[{label}]")
    if music_index is not None:
        label = f"m{label_index}"
        label_index += 1
        filters.append(f"[{music_index}:a]volume={music_gain_db}dB[{label}]")
        mix_inputs.append(f"[{label}]")
    if sfx_index is not None:
        label = f"x{label_index}"
        label_index += 1
        filters.append(f"[{sfx_index}:a]volume={sfx_gain_db}dB[{label}]")
        mix_inputs.append(f"[{label}]")
    if not mix_inputs:
        return {"ok": False, "error": "audio_mix_requires_music_or_sfx_or_source_audio"}

    if len(mix_inputs) == 1:
        filters.append(f"{mix_inputs[0]}anull[aout]")
    else:
        filters.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2[aout]"
        )
    out_audio_label = "[aout]"
    if normalize_loudness:
        filters.append(f"[aout]loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11[norm]")
        filters.append("[norm]alimiter=limit=0.98[aout_final]")
        out_audio_label = "[aout_final]"

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            out_audio_label,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_ffmpeg_timeout_s(),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": "ffmpeg_timeout",
            "stdout": (exc.stdout or "").strip()[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip()[-8000:] if isinstance(exc.stderr, str) else "",
            "out_exists": out_path.exists(),
            "out_path": str(out_path),
        }
    return {
        "ok": completed.returncode == 0 and out_path.exists(),
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-8000:],
        "stderr": (completed.stderr or "").strip()[-8000:],
        "out_exists": out_path.exists(),
        "out_path": str(out_path),
    }


def _build_insights_summary(
    *,
    metrics_rows: list[MetricsDaily],
    publish_rows: list[PublishRecord],
    intro_audit_rows: list[AuditEvent] | None = None,
    now: datetime,
) -> dict:
    utc_now = now.astimezone(timezone.utc)
    today = utc_now.date()
    windows = [
        ("24h", 1),
        ("72h", 3),
        ("7d", 7),
        ("14d", 14),
    ]

    def _row_totals(rows: list[MetricsDaily], days: int) -> dict:
        from_day = today - timedelta(days=days - 1)
        selected = [row for row in rows if row.date and row.date >= from_day]
        views = int(sum(int(row.views or 0) for row in selected))
        likes = int(sum(int(row.likes or 0) for row in selected))
        comments = int(sum(int(row.comments or 0) for row in selected))
        shares = int(sum(int(row.shares or 0) for row in selected))
        watch_time_seconds = int(sum(int(row.watch_time_seconds or 0) for row in selected))
        avg_view_percentage = None
        if views > 0:
            weighted = 0.0
            for row in selected:
                row_views = int(row.views or 0)
                row_pct = row.avg_view_percentage
                if row_views > 0 and row_pct is not None:
                    weighted += float(row_pct) * row_views
            avg_view_percentage = weighted / views if weighted > 0 else None
        publish_from = utc_now - timedelta(days=days)
        published = 0
        for record in publish_rows:
            if record.status not in {"published", "manual_confirmed"}:
                continue
            source_ts = record.published_at or record.created_at
            if source_ts and source_ts >= publish_from:
                published += 1
        interactions = likes + comments + shares
        engagement_rate = (interactions / views) if views > 0 else None
        return {
            "days": days,
            "from_date": str(from_day),
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "watch_time_seconds": watch_time_seconds,
            "avg_view_percentage": avg_view_percentage,
            "engagement_rate": engagement_rate,
            "published_count": published,
        }

    by_window = {label: _row_totals(metrics_rows, days) for label, days in windows}

    content_rollup: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time_seconds": 0}
    )
    recent_from = today - timedelta(days=13)
    for row in metrics_rows:
        if not row.date or row.date < recent_from:
            continue
        key = (str(row.platform_type or "unknown"), str(row.content_id or "unknown"))
        bucket = content_rollup[key]
        bucket["views"] += int(row.views or 0)
        bucket["likes"] += int(row.likes or 0)
        bucket["comments"] += int(row.comments or 0)
        bucket["shares"] += int(row.shares or 0)
        bucket["watch_time_seconds"] += int(row.watch_time_seconds or 0)

    top_content = []
    for (platform, content_id), agg in content_rollup.items():
        views = agg["views"]
        interactions = agg["likes"] + agg["comments"] + agg["shares"]
        top_content.append(
            {
                "platform": platform,
                "content_id": content_id,
                "views": views,
                "engagement_rate": (interactions / views) if views > 0 else None,
                "watch_time_seconds": agg["watch_time_seconds"],
            }
        )
    top_content.sort(key=lambda item: int(item.get("views") or 0), reverse=True)

    w24 = by_window["24h"]
    w72 = by_window["72h"]
    w7 = by_window["7d"]
    recommendation_code = "insufficient_data"
    recommendation = "Collect at least 24h metrics to generate recommendations."
    if int(w24["views"]) > 0 or int(w72["views"]) > 0:
        retention = w72["avg_view_percentage"]
        engagement = w72["engagement_rate"]
        if retention is not None and retention < 35.0:
            recommendation_code = "improve_pacing"
            recommendation = "Retention is low. Tighten pacing and show core action earlier."
        elif engagement is not None and engagement < 0.03:
            recommendation_code = "improve_hook"
            recommendation = "Engagement is low. Strengthen intro hook and first 2 seconds."
        elif int(w24["views"]) < max(100, int(w7["views"] / 7) if int(w7["views"]) > 0 else 100):
            recommendation_code = "increase_distribution"
            recommendation = "Recent reach is below weekly baseline. Test stronger title/hashtags and posting slot."
        else:
            recommendation_code = "keep_iteration"
            recommendation = "Current pattern performs acceptably. Keep style and iterate on variants."

    audio_profiles_rollup: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "rows": 0,
            "views": 0,
            "watch_time_seconds": 0,
            "avg_view_percentage_weighted": 0.0,
            "avg_view_duration_seconds_weighted": 0.0,
            "views_for_avg_pct": 0,
            "views_for_avg_duration": 0,
        }
    )
    for row in metrics_rows:
        if not row.date or row.date < recent_from:
            continue
        if not isinstance(row.extra_metrics, dict):
            continue
        profile = row.extra_metrics.get("audio_profile")
        if not isinstance(profile, str) or not profile.strip():
            continue
        key = profile.strip().lower()
        bucket = audio_profiles_rollup[key]
        views = int(row.views or 0)
        bucket["rows"] += 1
        bucket["views"] += views
        bucket["watch_time_seconds"] += int(row.watch_time_seconds or 0)
        if row.avg_view_percentage is not None and views > 0:
            bucket["avg_view_percentage_weighted"] += float(row.avg_view_percentage) * views
            bucket["views_for_avg_pct"] += views
        if row.avg_view_duration_seconds is not None and views > 0:
            bucket["avg_view_duration_seconds_weighted"] += float(row.avg_view_duration_seconds) * views
            bucket["views_for_avg_duration"] += views

    audio_profiles_14d = []
    for profile, bucket in audio_profiles_rollup.items():
        pct_den = int(bucket["views_for_avg_pct"])
        dur_den = int(bucket["views_for_avg_duration"])
        avg_pct = (float(bucket["avg_view_percentage_weighted"]) / pct_den) if pct_den > 0 else None
        avg_duration = (float(bucket["avg_view_duration_seconds_weighted"]) / dur_den) if dur_den > 0 else None
        audio_profiles_14d.append(
            {
                "audio_profile": profile,
                "rows": int(bucket["rows"]),
                "views": int(bucket["views"]),
                "watch_time_seconds": int(bucket["watch_time_seconds"]),
                "avg_view_percentage": avg_pct,
                "avg_view_duration_seconds": avg_duration,
            }
        )
    audio_profiles_14d.sort(key=lambda item: item["views"], reverse=True)

    intro_rows = intro_audit_rows or []
    intro_total = 0
    intro_attempted = 0
    intro_translated = 0
    intro_fallback = 0
    intro_empty_result = 0
    intro_disabled = 0
    intro_other = 0
    for row in intro_rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        translation_meta = payload.get("translation_meta")
        if not isinstance(translation_meta, dict):
            continue
        intro_total += 1
        attempted = bool(translation_meta.get("attempted", True))
        if attempted:
            intro_attempted += 1
        else:
            reason = str(translation_meta.get("reason", "")).strip().lower()
            if reason == "disabled_by_env":
                intro_disabled += 1
            else:
                intro_other += 1
            continue
        status = str(translation_meta.get("status", "")).strip().lower()
        if status == "translated":
            intro_translated += 1
        elif status == "fallback":
            intro_fallback += 1
        elif status == "empty_result":
            intro_empty_result += 1
        else:
            intro_other += 1

    fallback_numerator = intro_fallback + intro_empty_result
    intro_translate_14d = {
        "rows_total": intro_total,
        "attempted": intro_attempted,
        "translated": intro_translated,
        "fallback": intro_fallback,
        "empty_result": intro_empty_result,
        "disabled": intro_disabled,
        "other": intro_other,
        "fallback_share_attempted": (fallback_numerator / intro_attempted) if intro_attempted > 0 else None,
    }

    return {
        "generated_at": utc_now.isoformat(),
        "windows": by_window,
        "top_content_14d": top_content[:5],
        "audio_profiles_14d": audio_profiles_14d,
        "intro_translate_14d": intro_translate_14d,
        "recommendation_code": recommendation_code,
        "recommendation": recommendation,
    }


@app.post("/ops/godot/validate")
def ops_godot_validate(
    request: GodotManualRunRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        result = _ops_godot_run_mode(mode="validate", request=request)
        _audit_event(
            session,
            event_type="godot_manual_validate",
            actor_user_id=request.actor,
            payload={"script_path": result["script_path"], "log_file": result.get("log_file")},
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="validate",
                ok=True,
                actor_user_id=request.actor,
                payload=result,
            )
        )
        session.commit()
        return jsonable_encoder(result)
    except HTTPException as exc:
        session.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="validate",
                ok=False,
                actor_user_id=request.actor,
                payload=detail,
                error=None if detail else str(exc.detail),
            )
        )
        raise
    finally:
        session.close()


@app.post("/ops/godot/estimate-duration")
def ops_godot_estimate_duration(
    request: GodotEstimateDurationRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        script_path = Path(request.script_path).expanduser().resolve()
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="script_not_found")
        if script_path.suffix != ".gd":
            raise HTTPException(status_code=400, detail="script_must_be_gd")

        result = _run_godot_manual_step(
            mode="estimate",
            script_path=script_path,
            seconds=request.scout_seconds,
            fps=request.fps,
            max_nodes=request.max_nodes,
            estimate_threshold=request.threshold,
            estimate_hold_seconds=request.hold_seconds,
            estimate_sample_seconds=request.sample_seconds,
        )
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result)

        estimate = result.get("estimate") if isinstance(result.get("estimate"), dict) else {}
        intent_payload = _intent_recommendation(
            estimate=estimate,
            target_duration_s=request.target_duration_s,
            scout_seconds=request.scout_seconds,
            tail_seconds=request.tail_seconds,
        )
        payload = {
            **result,
            "target_duration_s": request.target_duration_s,
            "scout_seconds": request.scout_seconds,
            "tail_seconds": request.tail_seconds,
            "target_runtime_s": _resolve_target_runtime_s(),
            **intent_payload,
        }

        _audit_event(
            session,
            event_type="godot_manual_estimate_duration",
            actor_user_id=request.actor,
            payload={
                "script_path": str(script_path),
                "target_duration_s": request.target_duration_s,
                "recommended_sim_duration_s": payload["recommended_sim_duration_s"],
                "confidence": payload["confidence"],
                "method": payload["method"],
                "log_file": result.get("log_file"),
            },
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="estimate",
                ok=True,
                actor_user_id=request.actor,
                payload=payload,
            )
        )
        session.commit()
        return jsonable_encoder(payload)
    except HTTPException as exc:
        session.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="estimate",
                ok=False,
                actor_user_id=request.actor,
                payload=detail,
                error=None if detail else str(exc.detail),
            )
        )
        raise
    finally:
        session.close()


@app.post("/ops/godot/preview")
def ops_godot_preview(
    request: GodotManualRunRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        result = _ops_godot_run_mode(mode="preview", request=request)
        _audit_event(
            session,
            event_type="godot_manual_preview",
            actor_user_id=request.actor,
            payload={
                "script_path": result["script_path"],
                "out_path": result.get("out_path"),
                "log_file": result.get("log_file"),
            },
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="preview",
                ok=True,
                actor_user_id=request.actor,
                payload=result,
            )
        )
        session.commit()
        return jsonable_encoder(result)
    except HTTPException as exc:
        session.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="preview",
                ok=False,
                actor_user_id=request.actor,
                payload=detail,
                error=None if detail else str(exc.detail),
            )
        )
        raise
    finally:
        session.close()


@app.post("/ops/godot/intent-check")
def ops_godot_intent_check(
    request: GodotIntentCheckRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        script_path = Path(request.script_path).expanduser().resolve()
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="script_not_found")
        if script_path.suffix != ".gd":
            raise HTTPException(status_code=400, detail="script_must_be_gd")

        target_runtime_s = _resolve_target_runtime_s(request.runtime_override_s)
        result = _run_godot_manual_step(
            mode="estimate",
            script_path=script_path,
            seconds=request.scout_seconds,
            fps=request.fps,
            max_nodes=request.max_nodes,
            estimate_threshold=request.threshold,
            estimate_hold_seconds=request.hold_seconds,
            estimate_sample_seconds=request.sample_seconds,
        )
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result)

        estimate = result.get("estimate") if isinstance(result.get("estimate"), dict) else {}
        intent_payload = _intent_recommendation(
            estimate=estimate,
            target_duration_s=target_runtime_s,
            scout_seconds=request.scout_seconds,
            tail_seconds=request.tail_seconds,
        )
        payload = {
            **result,
            "mode": "intent_check",
            "scout_seconds": request.scout_seconds,
            "tail_seconds": request.tail_seconds,
            "target_runtime_s": target_runtime_s,
            "runtime_override_s": request.runtime_override_s,
            "target_duration_s": target_runtime_s,
            **intent_payload,
        }

        _audit_event(
            session,
            event_type="godot_manual_intent_check",
            actor_user_id=request.actor,
            payload={
                "script_path": str(script_path),
                "target_runtime_s": target_runtime_s,
                "intent_status": payload["intent_status"],
                "recommended_sim_duration_s": payload["recommended_sim_duration_s"],
                "recommended_speed_factor": payload["recommended_speed_factor"],
                "log_file": result.get("log_file"),
            },
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="intent_check",
                ok=True,
                actor_user_id=request.actor,
                payload=payload,
            )
        )
        session.commit()
        return jsonable_encoder(payload)
    except HTTPException as exc:
        session.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="intent_check",
                ok=False,
                actor_user_id=request.actor,
                payload=detail,
                error=None if detail else str(exc.detail),
            )
        )
        raise
    finally:
        session.close()


@app.post("/ops/godot/render")
def ops_godot_render(
    request: GodotManualRunRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        result = _ops_godot_run_mode(mode="render", request=request)
        _audit_event(
            session,
            event_type="godot_manual_render",
            actor_user_id=request.actor,
            payload={
                "script_path": result["script_path"],
                "out_path": result.get("out_path"),
                "log_file": result.get("log_file"),
            },
        )
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="render",
                ok=True,
                actor_user_id=request.actor,
                payload=result,
            )
        )
        session.commit()
        return jsonable_encoder(result)
    except HTTPException as exc:
        session.rollback()
        detail = exc.detail if isinstance(exc.detail, dict) else None
        _append_manual_godot_history(
            _manual_godot_history_record(
                step="render",
                ok=False,
                actor_user_id=request.actor,
                payload=detail,
                error=None if detail else str(exc.detail),
            )
        )
        raise
    finally:
        session.close()


@app.post("/ops/overlay/intro")
def ops_overlay_intro(
    request: IntroOverlayRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        input_path = Path(request.input_path).expanduser().resolve()
        if not input_path.exists():
            raise HTTPException(status_code=404, detail="input_video_not_found")

        out_path = (
            Path(request.out_path).expanduser().resolve()
            if request.out_path
            else input_path.with_name(f"{input_path.stem}.intro.mp4")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        language = (request.language or getenv("OPERATOR_INTRO_LANGUAGE", "en") or "en").strip().lower()
        if language not in {"pl", "en"}:
            language = "en"
        text_value = (request.intro_text or "").strip()
        if not text_value and request.idea_id is not None:
            idea = session.get(Idea, request.idea_id)
            if idea is None:
                raise HTTPException(status_code=404, detail="idea_not_found")
            text_value = _build_intro_text_from_idea(idea, language)
        if not text_value:
            raise HTTPException(status_code=400, detail="intro_text_or_idea_id_required")
        translation_meta: dict | None = None
        if language == "en":
            translated_value, translation_meta = _translate_intro_text_to_en(
                text=text_value,
                max_chars=request.max_chars,
            )
            if translated_value:
                text_value = translated_value
        text_value = _sanitize_intro_text(text=text_value, language=language, max_chars=request.max_chars)

        result = _run_intro_overlay_ffmpeg(
            input_path=input_path,
            out_path=out_path,
            text=text_value,
            duration_s=request.duration_s,
            font_size=request.font_size,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)

        payload = {
            **result,
            "input_path": str(input_path),
            "intro_text": text_value,
            "language": language,
            "duration_s": request.duration_s,
            "font_size": request.font_size,
            "idea_id": str(request.idea_id) if request.idea_id else None,
            "translation_meta": translation_meta,
        }
        _audit_event(
            session,
            event_type="intro_overlay_generate",
            actor_user_id=request.actor,
            payload={
                "input_path": str(input_path),
                "out_path": str(out_path),
                "language": language,
                "duration_s": request.duration_s,
                "font_size": request.font_size,
                "idea_id": str(request.idea_id) if request.idea_id else None,
                "translation_meta": translation_meta,
            },
        )
        session.commit()
        return jsonable_encoder(payload)
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()


@app.post("/ops/audio/mix")
def ops_audio_mix(
    request: AudioMixRequest,
    _guard: None = Depends(_require_operator),
) -> dict:
    session = SessionLocal()
    try:
        input_path = Path(request.input_path).expanduser().resolve()
        if not input_path.exists():
            raise HTTPException(status_code=404, detail="input_video_not_found")
        music_path = Path(request.music_path).expanduser().resolve() if request.music_path else None
        sfx_path = Path(request.sfx_path).expanduser().resolve() if request.sfx_path else None
        if music_path is not None and not music_path.exists():
            raise HTTPException(status_code=404, detail="music_path_not_found")
        if sfx_path is not None and not sfx_path.exists():
            raise HTTPException(status_code=404, detail="sfx_path_not_found")
        if music_path is None and sfx_path is None and not request.keep_source_audio:
            raise HTTPException(status_code=400, detail="audio_mix_requires_music_or_sfx_or_source_audio")

        out_path = (
            Path(request.out_path).expanduser().resolve()
            if request.out_path
            else input_path.with_name(f"{input_path.stem}.audio.mp4")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        result = _run_audio_mix_ffmpeg(
            input_path=input_path,
            out_path=out_path,
            music_path=music_path,
            sfx_path=sfx_path,
            keep_source_audio=request.keep_source_audio,
            music_gain_db=request.music_gain_db,
            sfx_gain_db=request.sfx_gain_db,
            normalize_loudness=request.normalize_loudness,
            target_lufs=request.target_lufs,
            true_peak_db=request.true_peak_db,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)

        payload = {
            **result,
            "input_path": str(input_path),
            "music_path": str(music_path) if music_path else None,
            "sfx_path": str(sfx_path) if sfx_path else None,
            "keep_source_audio": request.keep_source_audio,
            "music_gain_db": request.music_gain_db,
            "sfx_gain_db": request.sfx_gain_db,
            "normalize_loudness": request.normalize_loudness,
            "target_lufs": request.target_lufs,
            "true_peak_db": request.true_peak_db,
            "audio_profile": request.audio_profile,
        }
        _audit_event(
            session,
            event_type="audio_mix_generate",
            actor_user_id=request.actor,
            payload={
                "input_path": str(input_path),
                "out_path": str(out_path),
                "music_path": str(music_path) if music_path else None,
                "sfx_path": str(sfx_path) if sfx_path else None,
                "keep_source_audio": request.keep_source_audio,
                "music_gain_db": request.music_gain_db,
                "sfx_gain_db": request.sfx_gain_db,
                "normalize_loudness": request.normalize_loudness,
                "target_lufs": request.target_lufs,
                "true_peak_db": request.true_peak_db,
                "audio_profile": request.audio_profile,
            },
        )
        session.commit()
        return jsonable_encoder(payload)
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()
