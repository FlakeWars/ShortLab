from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
from os import getenv
from pathlib import Path
from typing import List, Optional, Literal
from uuid import UUID
from uuid import uuid4

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
from ideas.generator import IdeaDraft, generate_ideas, save_ideas
from ideas.parser import parse_ideas_text
from llm import get_mediator
from llm.mediator import _load_route, _load_routes

app = FastAPI(title="ShortLab API", version="0.1.0")

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/system/status")
def system_status() -> dict:
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

    return {
        "service_status": services,
        "repo_counts": repo_counts,
        "worker": worker,
        "dsl_version_current": current_dsl_version if "current_dsl_version" in locals() else None,
        "updated_at": updated_at,
        "partial_failures": partial_failures,
    }


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
        "operator_guard": flag("OPERATOR_TOKEN", "") != "",
        "artifacts_base_dir": flag("ARTIFACTS_BASE_DIR", "out"),
        "openai_model": flag("OPENAI_MODEL", ""),
        "openai_base_url": flag("OPENAI_BASE_URL", ""),
        "openai_temperature": flag("OPENAI_TEMPERATURE", "0.7"),
        "openai_max_output_tokens": flag("OPENAI_MAX_OUTPUT_TOKENS", "800"),
        "llm_token_budgets": flag("LLM_TOKEN_BUDGETS", ""),
    }


@app.get("/debug/llm-routes")
def debug_llm_routes(_guard: None = Depends(_require_operator)) -> dict:
    tasks = [
        "idea_generate",
        "idea_verify_capability",
        "idea_compile_dsl",
        "dsl_repair",
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

        stmt = (
            select(IdeaCandidate)
            .where(
                IdeaCandidate.status.in_(["new", "later"]),
                IdeaCandidate.capability_status == "feasible",
            )
            .order_by(func.random())
            .limit(limit)
        )
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
        if picked_candidate.capability_status != "feasible":
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

        candidate.status = "rejected"
        candidate.selected = False
        candidate.selected_at = None
        candidate.decision_at = datetime.now(timezone.utc)
        candidate.decision_by = None
        session.add(candidate)

        session.add(
            AuditEvent(
                event_type="idea_candidate_delete",
                source="ui",
                occurred_at=datetime.now(timezone.utc),
                payload={"idea_candidate_id": str(candidate.id), "action": "soft_delete"},
            )
        )
        session.commit()
        return jsonable_encoder({"id": candidate.id, "status": candidate.status})
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

        if not drafts:
            return jsonable_encoder({"created": 0, "skipped": 0, "idea_candidate_ids": []})

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
