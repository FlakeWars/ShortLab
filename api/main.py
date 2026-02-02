from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, select

from db.models import AuditEvent, IdeaCandidate, IdeaEmbedding, MetricsDaily
from db.session import SessionLocal

app = FastAPI(title="ShortLab API", version="0.1.0")


def _paginate(limit: int, offset: int) -> tuple[int, int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return limit, offset


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
