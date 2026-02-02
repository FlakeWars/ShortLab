from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from os import getenv
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select

from db.models import (
    Animation,
    AuditEvent,
    Artifact,
    IdeaCandidate,
    IdeaEmbedding,
    MetricsDaily,
    QCDecision,
    Render,
    Job,
)
from db.session import SessionLocal
from pipeline.queue import enqueue_pipeline, enqueue_render

app = FastAPI(title="ShortLab API", version="0.1.0")


def _paginate(limit: int, offset: int) -> tuple[int, int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return limit, offset


def _encode(obj) -> dict:
    return jsonable_encoder(obj)


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


class RerunRequest(BaseModel):
    animation_id: UUID
    out_root: str = Field(default="out/pipeline")


class CleanupRequest(BaseModel):
    older_min: int = Field(default=30, ge=1, le=1440)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
    similarity_status: Optional[str] = None,
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
        if similarity_status:
            stmt = stmt.where(IdeaCandidate.similarity_status == similarity_status)
        if selected is not None:
            stmt = stmt.where(IdeaCandidate.selected == selected)
        stmt = stmt.order_by(desc(IdeaCandidate.created_at)).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return jsonable_encoder(rows)
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
        }
    finally:
        session.close()


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
    result = enqueue_pipeline(
        request.dsl_template,
        request.out_root,
        request.idea_gate,
    )
    return jsonable_encoder(result)


@app.post("/ops/rerun")
def ops_rerun(request: RerunRequest, _guard: None = Depends(_require_operator)) -> dict:
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
